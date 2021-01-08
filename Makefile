################################################################################
# (c) 2021 Copyright, Real-Time Innovations, Inc. (RTI)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

DIST_DIR := dist
BUILD_DIR := build
EGG_DIR := yaml_serde.egg-info
PKG_DIR := yaml_serde

VERSION = $(shell cat VERSION)

VERSION_FILES := $(PKG_DIR)/__init__.py \
                 setup.py \
                 VERSION

PY_SOURCE := $(shell find $(PKG_DIR) -name "*.py")

DEPS_PIP := wheel \
            setuptools \
            bumpversion \
            twine
DEPS_APT := python3-pip

define DIST_TGT
$(shell bash -c 'ls $(DIST_DIR)/yaml{_,-}serde-$(VERSION)*')
endef

VENV_DIR ?= venv

ifneq (NATIVE,)
VENV_ACTIVATE := . $(VENV_DIR)/bin/activate &&
endif

define VENV_EXEC
$(VENV_ACTIVATE) $(1)
endef

REQUIREMENTS ?= requirements.txt

build: venv.install
	$(call VENV_EXEC, python3 setup.py sdist bdist_wheel)

clean:
	rm -rf $(DIST_DIR) $(BUILD_DIR) $(EGG_DIR)

twine.check:
	$(call VENV_EXEC, twine check $(call DIST_TGT))

twine.upload:
	$(call VENV_EXEC, \
		twine upload --repository-url https://test.pypi.org/legacy/ \
		    $(call DIST_TGT))

pypi.upload:
	$(call VENV_EXEC, twine upload $(call DIST_TGT))

bumpversion.%:
	$(call VENV_EXEC, \
		bumpversion --current-version $(shell cat VERSION) \
			$* $(VERSION_FILES))

bump.minor: bumpversion.minor
bump.major: bumpversion.major
bump.patch: bumpversion.patch

deps.pip:
	pip3 install -U $(DEPS_PIP)

deps.apt:
	sudo apt install $(DEPS_APT)

deps: deps.apt \
      deps.pip

venv.init: $(VENV_DIR)

$(VENV_DIR):
	python3 -m venv $@

venv.clean:
	rm -rf $(VENV_DIR)

clean: venv.clean

venv.install-deps: $(VENV_DIR)
	$(call VENV_EXEC, pip install -U $(DEPS_PIP))

venv.install: venv.install-deps
	$(call VENV_EXEC, pip install -e .)

venv.freeze:
	$(call VENV_EXEC, python3 -m pip freeze > $(REQUIREMENTS))

dev: venv.install \
     foo.tar.gz
	@echo -- initialize python venv. Use \`. venv/bin/activate\` to enable it

foo.tar.gz: foo
	tar cvzf $@ $<

foo:
	mkdir -p foo/bar
	touch foo/bar/baz

foo.clean:
	rm -rf foo foo.tar.gz

clean: foo.clean

%.tag-release: %.tag %.tag-push
	@echo -- Released tag: $*

%.tag:
	@[ -n "$*" ] || (echo Invalid tag >&2 && exit 1)
	@[ -n "$(MESSAGE)" ] || \
		(echo Invalid tag message. Use MESSAGE to specify one >&2 && exit 1)
	@[ -z "$$(git tag -l | grep '^$*$$')" ] || \
	    (echo Tag '$*' already exists. >&2 && exit 1)
	@echo -- Tagging repository: $* "("$(MESSAGE)")"
	git tag -a $* -m "$(MESSAGE)"
	@echo -- Created tag: $*

%.tag-push:
	@[ -n "$*" ] || (echo Invalid tag >&2 && exit 1)
	git push origin $*
	@echo -- Pushed tag: $*

%.tag-delete:
	@[ -n "$*" ] || (echo Invalid tag >&2 && exit 1)
	git tag -d $*
	@echo -- Deleted tag: $*

%.tag-delete-remote:
	@[ -n "$*" ] || (echo Invalid tag >&2 && exit 1)
	git push origin :refs/tags/$*
	@echo -- Deleted remote tag: $*

tag-push:
	git push origin --tags
	@echo -- Pushed all tags

release: $(VERSION).release

release-push: $(VERSION).release-push

release-abort: $(VERSION).release-abort

%.release-build: clean \
                 build
	@echo -- Built new release: $*

%.release: %.release-build \
           %.tag
        #    build \
		#    twine.check \
		#    twine.upload
	@echo -- Generated new release: $*

%.release-abort: %.tag-delete
    @echo -- Aborted release: $*

%.release-push: %.tag-push \
                pypi.upload
	@echo -- Pushed new release: $*

.PHONY: clean \
        build \
        twine.check \
        twine.upload \
        pypi.upload \
        bump.minor \
        bump.major \
        bump.patch \
        deps \
        deps.pip \
        deps.apt \
        venv.clean \
        venv.install \
		venv.freeze \
        tag-push \
        release \
        release-push \
        release-abort
