TARGET := iphone:clang:latest:15.0
ARCHS = arm64 arm64e

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = DazzPro
DazzPro_FILES = Tweak.xm
DazzPro_CFLAGS = -fobjc-arc -Wno-unused-function -Wno-unused-variable
DazzPro_FRAMEWORKS = Foundation UIKit

include $(THEOS_MAKE_PATH)/tweak.mk

after-install::
	install.exec "killall -9 DazzCamera || true"