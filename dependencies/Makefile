.PHONY: install
install:install_libFuzzerMutator pc_sampling

pc_sampling:
	cd pc_sampling && $(MAKE) -j1

install_qemu:
	echo ***** Clone qemu
	git clone --depth 1 -j8  https://github.com/qemu/qemu.git

install_libFuzzerMutator:
	echo '***** Download libFuzzer Mutator (AFL++ git repo stores libFuzzer Mutator code)'
	#git clone --branch dev https://github.com/AFLplusplus/AFLplusplus.git
	cd AFLplusplus && git checkout 550ba4d77294e61597a5259d00769c61281e0042
	cp -r AFLplusplus/custom_mutators/libfuzzer libFuzzerSrc
	echo "use our own Makefile instead of AFL++'s Makefile, because AFL++'s Makefile links in AFL++ related code which we don't need"
	cp ../src/libfuzzer/Makefile libFuzzerSrc/Makefile
	cd libFuzzerSrc && make -j4

clean:
	rm -rf libFuzzerSrc
	cd pc_sampling && $(MAKE) clean
