REPONAME=digital-crimes/mimir
BUILDROOT=$(HOME)/dockerbuild/$(REPONAME)
DOCKERREPO=docker-dcu-local.artifactory.secureserver.net/mimir
SHELL=/bin/bash
DATE=$(shell date)
COMMIT=
BUILD_BRANCH=origin/master

# libraries we need to stage for pip to install inside Docker build

PRIVATE_PIPS="git@github.secureserver.net:auth-contrib/PyAuth.git" \
"git@github.com:gdcorp-infosec/dcu-structured-logging-flask.git" \
git@github.secureserver.net:digital-crimes/dcdatabase.git

.PHONY: prep flake8 isort tools test testcov dev stage prod ote clean prod-deploy ote-deploy dev-deploy

all: env

env:
	pip3 install -r test_requirements.txt
	pip3 install -r private_pips.txt
	pip3 install -r requirements.txt

flake8:
	@echo "----- Running linter -----"
	flake8 --config ./.flake8 .

isort:
	@echo "----- Optimizing imports -----"
	python -m isort --atomic --skip .venv .

tools: flake8 isort

test:
	@echo "----- Running tests -----"
	nosetests tests

testcov:
	@echo "----- Running tests with coverage -----"
	nosetests tests --with-coverage --cover-erase --cover-package=mimir


prep: tools test
	@echo "----- preparing $(REPONAME) build -----"
	# stage pips we will need to install in Docker build
	mkdir -p $(BUILDROOT)/private_pips && rm -rf $(BUILDROOT)/private_pips/*
	for entry in $(PRIVATE_PIPS) ; do \
		IFS=";" read repo revision <<< "$$entry" ; \
		cd $(BUILDROOT)/private_pips && git clone $$repo ; \
		if [ "$$revision" != "" ] ; then \
			name=$$(echo $$repo | awk -F/ '{print $$NF}' | sed -e 's/.git$$//') ; \
			cd $(BUILDROOT)/private_pips/$$name ; \
			current_revision=$$(git rev-parse HEAD) ; \
			echo $$repo HEAD is currently at revision: $$current_revision ; \
			echo Dependency specified in the Makefile for $$name is set to revision: $$revision ; \
			echo Reverting to revision: $$revision in $$repo ; \
			git reset --hard $$revision; \
		fi ; \
	done

	# copy the app code to the build root
	cp -rp ./* $(BUILDROOT)

prod: prep
	@echo "----- building $(REPONAME) prod -----"
	read -p "About to build production image from $(BUILD_BRANCH) branch. Are you sure? (Y/N): " response ; \
	if [[ $$response == 'N' || $$response == 'n' ]] ; then exit 1 ; fi
	if [[ `git status --porcelain | wc -l` -gt 0 ]] ; then echo "You must stash your changes before proceeding" ; exit 1 ; fi
	git fetch && git checkout $(BUILD_BRANCH)
	$(eval COMMIT:=$(shell git rev-parse --short HEAD))
	sed -ie 's/THIS_STRING_IS_REPLACED_DURING_BUILD/$(DATE)/' $(BUILDROOT)/k8s/prod/mimir.deployment.yaml
	sed -ie 's/REPLACE_WITH_GIT_COMMIT/$(COMMIT)/' $(BUILDROOT)/k8s/prod/mimir.deployment.yaml
	docker build -t $(DOCKERREPO):$(COMMIT) $(BUILDROOT)
	git checkout -

ote: prep
	@echo "----- building $(REPONAME) ote -----"
	sed -ie 's/THIS_STRING_IS_REPLACED_DURING_BUILD/$(DATE)/g' $(BUILDROOT)/k8s/ote/mimir.deployment.yaml
	docker build -t $(DOCKERREPO):ote $(BUILDROOT)

dev: prep
	@echo "----- building $(REPONAME) dev -----"
	sed -ie 's/THIS_STRING_IS_REPLACED_DURING_BUILD/$(DATE)/g' $(BUILDROOT)/k8s/dev/mimir.deployment.yaml
	docker build -t $(DOCKERREPO):dev $(BUILDROOT)

prod-deploy: prod
	@echo "----- deploying $(REPONAME) prod -----"
	docker push $(DOCKERREPO):$(COMMIT)
	kubectl --context prod-dcu apply -f $(BUILDROOT)/k8s/prod/mimir.deployment.yaml --record

ote-deploy: ote
	@echo "----- deploying $(REPONAME) ote -----"
	docker push $(DOCKERREPO):ote
	kubectl --context ote-dcu apply -f $(BUILDROOT)/k8s/ote/mimir.deployment.yaml --record

dev-deploy: dev
	@echo "----- deploying $(REPONAME) dev -----"
	docker push $(DOCKERREPO):dev
	kubectl --context dev-dcu apply -f $(BUILDROOT)/k8s/dev/mimir.deployment.yaml --record

clean:
	@echo "----- cleaning $(REPONAME) app -----"
	rm -rf $(BUILDROOT)
