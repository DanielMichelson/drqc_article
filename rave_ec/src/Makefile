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
# rave_ec/src Makefile
# @file
# @author Daniel Michelson, Environment and Climate Change Canada
# @date 2016-05-26
###########################################################################
-include $(RAVEROOT)/rave/mkf/def.mk

RAVEECINC= -I. $(NUMPY_INCLUDE_DIR) $(INCLUDE_PYTHON) \
		-I$(HLHDF_INCLUDE_DIR) $(ZLIB_INCDIR) $(HDF5_INCDIR) \
		$(PROJ_INCLUDE_DIR) $(RAVE_INCLUDE_FLAG)

LDFLAGS+= -L. -L$(HLHDF_LIB_DIR) $(ZLIB_LIBDIR) $(HDF5_LIBDIR) $(PROJ_LIB_DIR) \
		$(RAVE_LIB_FLAG)

ifeq ($(EXPAT_SUPPRESSED), no)
RAVEECINC+= $(EXPAT_INCLUDE_DIR)
LDFLAGS+= $(EXPAT_LIB_DIR)
endif

ifeq ($(BUFR_SUPPRESSED), no)
RAVEECINC+= $(BUFR_INCLUDE_DIR)
LDFLAGS+= $(BUFR_LIB_DIR)
endif

CFLAGS=	$(OPTS) $(CCSHARED) $(DEFS) $(CREATE_ITRUNC) $(RAVEECINC)

# --------------------------------------------------------------------
# Fixed definitions

RAVEECSOURCES= raveec.c
INSTALL_HEADERS= raveec.h
RAVEECOBJS= $(RAVEECSOURCES:.c=.o)
LIBRAVEEC= libraveec.so
RAVEECMAIN= 
RAVEECBIN= raveec
RAVEECBINDEB= raveec_deb
RAVEECLIBS= -lraveec $(RAVE_MODULE_LIBRARIES)

MAKEDEPEND=gcc -MM $(CFLAGS) -o $(DF).d $<
DEPDIR=.dep
DF=$(DEPDIR)/$(*F)
# --------------------------------------------------------------------
# Rules

# Contains dependency generation as well, so if you are not using
# gcc, comment out everything until the $(CC) statement.
%.o : %.c
	@$(MAKEDEPEND); \
	cp $(DF).d $(DF).P; \
	sed -e 's/#.*//' -e 's/^[^:]*: *//' -e 's/ *\\$$//' \
		-e '/^$$/ d' -e 's/$$/ :/' < $(DF).d >> $(DF).P; \
	\rm -f $(DF).d
	$(CC) -c $(CFLAGS) $<

# Ensures that the .dep directory exists
.PHONY=$(DEPDIR)
$(DEPDIR):
	+@[ -d $@ ] || mkdir -p $@

.PHONY=all
all:		$(LIBRAVEEC) #bin

$(LIBRAVEEC): $(DEPDIR) $(RAVEECOBJS) 
	$(LDSHARED) -o $@ $(RAVEECOBJS)

.PHONY=bin
bin: 
	$(CC) $(RAVEECINC) $(LDFLAGS) -o $(RAVEECBIN) $(RAVEECOBJS) $(RAVEECLIBS)

.PHONY=bin-debug
bin-debug:		$(RAVEECBINDEB)

$(RAVEECBINDEB): $(RAVEECSOURCES)
	$(CC) $(CFLAGS) -c raveec.c -o raveec.o
	$(CC) $(CFLAGS) $(RAVEECINC) $(LDFLAGS) -o $(RAVEECBINDEB) $(RAVEECOBJS) $(RAVEECLIBS)

.PHONY=install
install:
	@"$(HLHDF_INSTALL_BIN)" -f -o -C $(LIBRAVEEC) "$(prefix)/lib/$(LIBRAVEEC)"
	@for i in $(INSTALL_HEADERS) ; \
	do \
		"$(HLHDF_INSTALL_BIN)" -f -o -m644 -C $$i "$(prefix)/include/$$i"; \
	done
#	"$(HLHDF_INSTALL_BIN)" -f -o -C $(RAVEECBIN) "$(prefix)/bin/$(RAVEECBIN)";

.PHONY=clean
clean:
		@\rm -f *.o core *~ $(LIBRAVEEC)
#		@\rm -fr $(DEPDIR)

.PHONY=distclean		 
distclean:	clean
		@\rm -f *.so

# NOTE! This ensures that the dependencies are setup at the right time so this should not be moved
-include $(RAVEECSOURCES:%.c=$(DEPDIR)/%.P)
