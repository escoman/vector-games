# Makefile — сборка всех тестовых ROM для Вектора-06Ц.
#
# make          — собрать все тестовые ROM;
# make clean    — убрать артефакты сборки всех тестов;
# make full     — clean + сборка всех тестов.

TESTS = 512x256 \
        cls \
        clrs \
        dt2 \
        dt2_512 \
        dt2_lz

.PHONY: all clean full

all:
	@for t in $(TESTS); do $(MAKE) -C $$t || exit 1; done
	@echo "=== All tests built ==="

clean:
	@for t in $(TESTS); do $(MAKE) -C $$t clean; done
	@echo "=== All tests cleaned ==="

full: clean all
