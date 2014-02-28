#
# Copyright (c) SAS Institute Inc.
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
#


TOPDIR=..

bin_files = spanner

extra_dist = Makefile


all: default-all 
	mkdir -p $(TOPDIR)/bin
	install -m755 spanner $(TOPDIR)/bin/spanner

install:
ifndef LIB_ONLY
	mkdir -p $(DESTDIR)$(bindir)
	for f in $(bin_files); do \
		install -m755 $$f $(DESTDIR)$(bindir)/$$f; \
	done
	for f in $(sbin_files); do \
		install -m755 $$f $(DESTDIR)$(sbindir)/$$f; \
	done
endif

dist: default-dist

clean: default-clean
	rm -rf $(TOPDIR)/bin

include $(TOPDIR)/Make.rules
include $(TOPDIR)/Make.defs
