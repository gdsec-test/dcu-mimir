REPONAME=digital-crimes/mimir
BUILDROOT=$(HOME)/dockerbuild/$(REPONAME)
DOCKERREPO=docker-dcu-local.artifactory.secureserver.net/mimir
SHELL=/bin/bash
DATE=$(shell date)
COMMIT=
BUILD_BRANCH=origin/main

define deploy_k8s
	docker push $(DOCKERREPO):$(2)
	cd k8s/$(1) && kustomize edit set image $$(docker inspect --format='{{index .RepoDigests 0}}' $(DOCKERREPO):$(2))
	kubectl --context $(1)-dcu apply -k k8s/$(1)
	cd k8s/$(1) && kustomize edit set image $(DOCKERREPO):$(1)
endef

.PHONY: prep flake8 isort tools test testcov dev stage prod ote clean prod-deploy ote-deploy dev-deploy

all: env

env:
	pip3 install -r test_requirements.txt
	pip3 install -r requirements.txt

flake8:
	@echo "----- Running linter -----"
	flake8 --config ./.flake8 .

isort:
	@echo "----- Optimizing imports -----"
	python -m isort --atomic --skip .venv .

tools: flake8 isort

test: tools
	@echo "----- Running tests -----"
	nosetests tests

testcov:
	@echo "----- Running tests with coverage -----"
	nosetests tests --with-coverage --cover-erase --cover-package=mimir


prep: tools test
	@echo "----- preparing $(REPONAME) build -----"
	mkdir -p $(BUILDROOT)/
	cp -rp ./* $(BUILDROOT)
	cp -rp ~/.pip $(BUILDROOT)/pip_config

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
	docker build -t $(DOCKERREPO):ote $(BUILDROOT)

test-env: prep
	@echo "----- building $(REPONAME) test -----"
	docker build -t $(DOCKERREPO):test $(BUILDROOT)

dev: prep
	@echo "----- building $(REPONAME) dev -----"
	docker build -t $(DOCKERREPO):dev $(BUILDROOT)

prod-deploy: prod
	@echo "----- deploying $(REPONAME) prod -----"
	$(call deploy_k8s,prod,$(COMMIT))


ote-deploy: ote
	@echo "----- deploying $(REPONAME) ote -----"
	$(call deploy_k8s,ote,ote)

test-deploy: test-env
	@echo "----- deploying $(REPONAME) test -----"
	$(call deploy_k8s,test,test)

dev-deploy: dev
	@echo "----- deploying $(REPONAME) dev -----"
	$(call deploy_k8s,dev,dev)

clean:
	@echo "----- cleaning $(REPONAME) app -----"
	rm -rf $(BUILDROOT)
