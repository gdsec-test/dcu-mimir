# Mimir (DCU Repeat Infractions Tracker)
There are many scenarios in which a compromised shopper or compromised hosting may have been compromised before. As of now, there are no systems to keep track of the history of compromises associated with a shopper or hosting account.
The immediate goal of this project is to provide a good way to track and enforce policies around repeat compromised hosting, repeat compromised shoppers, repeat intentionally malicious shoppers, and repeat domain suspensions. This will enable DCU investigators to be better informed during their investigations on phishnet.

## Table of Contents
  1. [Cloning](#cloning)
  2. [Installing Dependencies](#installing-dependencies)
  3. [Building](#building)
  4. [Deploying](#deploying)
  5. [Testing](#testing)
  6. [Style and Standards](#style-and-standards)
  7. [Built With](#built-with)
  8. [Running Locally](#running-locally)
  9. [Examples](#examples)

## Cloning
To clone the repository via SSH perform the following
```
git clone git@github.secureserver.net:digital-crimes/mimir.git
```

It is recommended that you clone this project into a pyvirtualenv or equivalent virtual environment. For this project, be sure to create a virtual environment with Python 3.6.
This is achievable via `mkproject --python=/usr/local/bin/python3.6 mimir`.

## Installing Dependencies
To install all dependencies for development and testing simply run `make`.

In case the installation for uwsgi fails, run an `apt-get install python3.6-dev` command. uWSCGI is a C application, so you need a C compiler (gcc or clang) and the Python development headers.

## Building
Building a local Docker image for the respective development environments can be achieved by
```
make [dev, ote, prod]
```

## Deploying
Deploying the Docker image to Kubernetes can be achieved via
```
make [dev, ote, prod]-deploy
```
You must also ensure you have the proper push permissions to Artifactory or you may experience a `Forbidden` message.

## Testing
```
make test     # runs all unit tests
make testcov  # runs tests with coverage
```

## Style and Standards
All deploys must pass Flake8 linting and all unit tests which are baked into the [Makefile](Makfile).

There are a few commands that might be useful to ensure consistent Python style:

```
make flake8  # Runs the Flake8 linter
make isort   # Sorts all imports
make tools   # Runs both Flake8 and isort
```

## Built With
Mimir is built utilizing the following key technologies

* Flask
* Flask Restplus
* Redis

## Running Locally
If you would like to run Mimir locally, you will need to specify the following environment variables
* `sysenv` (Set to `dev`. Other values include: `test`, `ote`, `prod`)
* `DB_PASS` (Password for MongoDB), writes to `infractions` collection

### Examples
Curl to POST Mimir infraction using CERT_JWT (view CN_WHITELIST in settings.py to obtain CN cert to use). Visit [this link](https://confluence.godaddy.com/display/ITSecurity/Accessing+Shopper+Locker+Service#AccessingShopperLockerService-ObtainaJWT) to view steps for requesting a cert JWT from a cert/key pair.

View Open API doc to determine valid values for `infractionType`.  All other values must be non-null/non-empty.
```
curl --location --request POST 'http://127.0.0.1:5000/v1/infractions' \
--header 'Content-Type: application/json' \
--header 'Authorization: WHITELISTED_JWT' \
--data-raw '{"infractionType": "SUSPENDED", "ticketId": "SampleTicket", "sourceDomainOrIp": "SampleDomain", "hostingGuid": "SampleGuid", "shopperId": "SampleShopperId"}'
```
Successful Output
```
{
    "infractionId": "SAMPLE_INFRACTION_ID"
}
```