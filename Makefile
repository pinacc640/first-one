# Makefile for linked list module

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -g -fPIC

# Shared library for Python ctypes
SHARED_LIB = liblinkedlist.so

# Test executable
TEST_BIN = test_linked_list

.PHONY: all clean lib test

all: lib $(TEST_BIN)

lib: $(SHARED_LIB)

$(SHARED_LIB): linked_list.c linked_list.h
	$(CC) $(CFLAGS) -shared -o $@ linked_list.c

$(TEST_BIN): linked_list.c linked_list.h
	$(CC) $(CFLAGS) -o $@ linked_list.c -DLINKED_LIST_MAIN

clean:
	rm -f $(SHARED_LIB) $(TEST_BIN) *.o
