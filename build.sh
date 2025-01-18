#!/bin/bash

# Permet la génération des paquets debian
TAG=$(git describe --tags $(git rev-list --tags --max-count=1))
VERSION="${TAG/-/"~"}"
fpm -t deb -v "$VERSION"