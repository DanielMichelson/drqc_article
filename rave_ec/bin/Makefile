###########################################################################
# Copyright (C) 2016 The Crown (i.e. Her Majesty the Queen in Right of Canada)
#
# This file is an add-on to RAVE.
#
# RAVE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# RAVE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with RAVE.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------
# 
# rave_ec/bin Makefile
# @file
# @author Daniel Michelson, Environment Canada and Climate Change Canada
# @date 2016-06-30
###########################################################################
-include $(RAVEROOT)/rave/mkf/def.mk

.PHONY=install
install:
	@mkdir -p "${prefix}/bin"
	@cp -v -f ecWxR_a2o "${prefix}/bin/"
	@cp -v -f ecWxR_convert "${prefix}/bin/"
	@cp -v -f ecWxR_qc "${prefix}/bin/"
	@cp -v -f janitor "${prefix}/bin/"
	@cp -v -f ecWxR_composite "${prefix}/bin/"
#	@cp -v -f l2o "${prefix}/bin/"
#	@cp -v -f test_pyinotify "${prefix}/bin/"

.PHONY:clean
clean: ;
	@\rm -f *~

.PHONY:distclean
distclean:
	@\rm -f *~
