.PHONY: default run inspect

default:
	# clang -sectcreate __TEXT __info_plist ./Info.plist -o macos_trace macos_trace.c
	clang test.s -o test
	clang -o macos_trace macos_trace.c

run: default
	sudo ./macos_trace

inspect:
	clang -S -o macos_trace.s macos_trace.c

clean:
	rm -f macos_trace
	rm -f test
	rm -f macos_trace.s