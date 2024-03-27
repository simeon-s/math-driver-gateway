
obj-m += src/math_chardev.o

math_chardev-objs := src/calcdev.o

KERNELDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	@mkdir -p ../build
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules
	mv src/math_chardev.ko ../build/ || true
	mv src/*.o src/*.mod.c src/*.symvers src/*.order ../build/ 2> /dev/null || true
	# Cleanup intermediate files
	@rm -f src/.math_chardev.ko.cmd src/.math_chardev.mod.cmd src/.math_chardev.mod.o.cmd src/.math_chardev.o.cmd src/math_chardev.mod
	@rm -f .Module.symvers.cmd .modules.order.cmd Module.symvers modules.order

clean:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) clean
	@rm -rf ../build/*chardev*
