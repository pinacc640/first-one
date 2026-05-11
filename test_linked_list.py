#!/usr/bin/env python3
"""
test_linked_list.py - Automated test script for the C linked list module.

This script:
1. Compiles the C linked list code into a shared library (liblinkedlist.so).
2. Loads the library via ctypes.
3. Runs a suite of tests covering all major operations.

Usage:
    python3 test_linked_list.py
"""

import ctypes
import os
import subprocess
import sys
import unittest


# Path to the shared library
LIB_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(LIB_DIR, "liblinkedlist.so")


def compile_library():
    """Compile the C linked list into a shared library."""
    source = os.path.join(LIB_DIR, "linked_list.c")
    if not os.path.exists(source):
        print(f"ERROR: Source file not found: {source}", file=sys.stderr)
        sys.exit(1)

    cmd = ["gcc", "-Wall", "-Wextra", "-std=c99", "-g", "-fPIC",
           "-shared", "-o", LIB_PATH, source]
    print(f"Compiling: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Compilation failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Compilation successful.")


def load_library():
    """Load the shared library and set up function signatures."""
    lib = ctypes.CDLL(LIB_PATH)

    # Define opaque pointer types
    class Node(ctypes.Structure):
        pass
    Node._fields_ = [
        ("data", ctypes.c_int),
        ("next", ctypes.POINTER(Node)),
    ]

    class LinkedList(ctypes.Structure):
        _fields_ = [
            ("head", ctypes.POINTER(Node)),
            ("size", ctypes.c_size_t),
        ]

    # list_create
    lib.list_create.restype = ctypes.POINTER(LinkedList)
    lib.list_create.argtypes = []

    # list_destroy
    lib.list_destroy.restype = None
    lib.list_destroy.argtypes = [ctypes.POINTER(LinkedList)]

    # list_insert_head
    lib.list_insert_head.restype = ctypes.c_int
    lib.list_insert_head.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_int]

    # list_insert_tail
    lib.list_insert_tail.restype = ctypes.c_int
    lib.list_insert_tail.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_int]

    # list_insert_at
    lib.list_insert_at.restype = ctypes.c_int
    lib.list_insert_at.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_size_t, ctypes.c_int]

    # list_delete
    lib.list_delete.restype = ctypes.c_int
    lib.list_delete.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_int]

    # list_delete_at
    lib.list_delete_at.restype = ctypes.c_int
    lib.list_delete_at.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_size_t]

    # list_search
    lib.list_search.restype = ctypes.POINTER(Node)
    lib.list_search.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_int]

    # list_get
    lib.list_get.restype = ctypes.c_int
    lib.list_get.argtypes = [ctypes.POINTER(LinkedList), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int)]

    # list_size
    lib.list_size.restype = ctypes.c_size_t
    lib.list_size.argtypes = [ctypes.POINTER(LinkedList)]

    # list_is_empty
    lib.list_is_empty.restype = ctypes.c_int
    lib.list_is_empty.argtypes = [ctypes.POINTER(LinkedList)]

    # list_reverse
    lib.list_reverse.restype = None
    lib.list_reverse.argtypes = [ctypes.POINTER(LinkedList)]

    return lib


class TestLinkedList(unittest.TestCase):
    """Test suite for the C linked list module."""

    @classmethod
    def setUpClass(cls):
        """Load the compiled shared library."""
        cls.lib = load_library()

    def setUp(self):
        """Create a fresh linked list for each test."""
        self.lst = self.lib.list_create()
        self.assertIsNotNone(self.lst)

    def tearDown(self):
        """Destroy the linked list after each test."""
        self.lib.list_destroy(self.lst)

    def test_create_empty_list(self):
        """A newly created list should be empty with size 0."""
        self.assertEqual(self.lib.list_size(self.lst), 0)
        self.assertEqual(self.lib.list_is_empty(self.lst), 1)

    def test_insert_head(self):
        """Insert at head should add elements in reverse order."""
        self.lib.list_insert_head(self.lst, 10)
        self.lib.list_insert_head(self.lst, 20)
        self.lib.list_insert_head(self.lst, 30)

        self.assertEqual(self.lib.list_size(self.lst), 3)

        val = ctypes.c_int()
        self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(val.value, 30)
        self.lib.list_get(self.lst, 1, ctypes.byref(val))
        self.assertEqual(val.value, 20)
        self.lib.list_get(self.lst, 2, ctypes.byref(val))
        self.assertEqual(val.value, 10)

    def test_insert_tail(self):
        """Insert at tail should add elements in order."""
        self.lib.list_insert_tail(self.lst, 1)
        self.lib.list_insert_tail(self.lst, 2)
        self.lib.list_insert_tail(self.lst, 3)

        self.assertEqual(self.lib.list_size(self.lst), 3)

        val = ctypes.c_int()
        self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(val.value, 1)
        self.lib.list_get(self.lst, 2, ctypes.byref(val))
        self.assertEqual(val.value, 3)

    def test_insert_at(self):
        """Insert at a specific index."""
        self.lib.list_insert_tail(self.lst, 1)
        self.lib.list_insert_tail(self.lst, 3)
        # Insert 2 at index 1 -> [1, 2, 3]
        ret = self.lib.list_insert_at(self.lst, 1, 2)
        self.assertEqual(ret, 0)
        self.assertEqual(self.lib.list_size(self.lst), 3)

        val = ctypes.c_int()
        self.lib.list_get(self.lst, 1, ctypes.byref(val))
        self.assertEqual(val.value, 2)

    def test_insert_at_invalid_index(self):
        """Insert at an invalid index should return -1."""
        ret = self.lib.list_insert_at(self.lst, 5, 99)
        self.assertEqual(ret, -1)

    def test_delete_by_value(self):
        """Delete first occurrence of a value."""
        self.lib.list_insert_tail(self.lst, 10)
        self.lib.list_insert_tail(self.lst, 20)
        self.lib.list_insert_tail(self.lst, 30)

        ret = self.lib.list_delete(self.lst, 20)
        self.assertEqual(ret, 0)
        self.assertEqual(self.lib.list_size(self.lst), 2)

        # 20 should no longer be found
        result = self.lib.list_search(self.lst, 20)
        self.assertFalse(result)

    def test_delete_nonexistent_value(self):
        """Deleting a value not in the list should return -1."""
        self.lib.list_insert_tail(self.lst, 10)
        ret = self.lib.list_delete(self.lst, 99)
        self.assertEqual(ret, -1)

    def test_delete_at(self):
        """Delete at a specific index."""
        self.lib.list_insert_tail(self.lst, 1)
        self.lib.list_insert_tail(self.lst, 2)
        self.lib.list_insert_tail(self.lst, 3)

        ret = self.lib.list_delete_at(self.lst, 1)
        self.assertEqual(ret, 0)
        self.assertEqual(self.lib.list_size(self.lst), 2)

        val = ctypes.c_int()
        self.lib.list_get(self.lst, 1, ctypes.byref(val))
        self.assertEqual(val.value, 3)

    def test_delete_at_invalid_index(self):
        """Delete at invalid index should return -1."""
        ret = self.lib.list_delete_at(self.lst, 0)
        self.assertEqual(ret, -1)

    def test_search_found(self):
        """Search for an existing value returns a valid pointer."""
        self.lib.list_insert_tail(self.lst, 42)
        result = self.lib.list_search(self.lst, 42)
        self.assertTrue(result)
        self.assertEqual(result.contents.data, 42)

    def test_search_not_found(self):
        """Search for a nonexistent value returns NULL."""
        self.lib.list_insert_tail(self.lst, 1)
        result = self.lib.list_search(self.lst, 999)
        self.assertFalse(result)

    def test_get_valid_index(self):
        """Get value at a valid index."""
        self.lib.list_insert_tail(self.lst, 100)
        val = ctypes.c_int()
        ret = self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(ret, 0)
        self.assertEqual(val.value, 100)

    def test_get_invalid_index(self):
        """Get at invalid index should return -1."""
        val = ctypes.c_int()
        ret = self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(ret, -1)

    def test_reverse(self):
        """Reverse the list."""
        for i in range(1, 6):
            self.lib.list_insert_tail(self.lst, i)

        self.lib.list_reverse(self.lst)

        val = ctypes.c_int()
        expected = [5, 4, 3, 2, 1]
        for i, exp in enumerate(expected):
            self.lib.list_get(self.lst, i, ctypes.byref(val))
            self.assertEqual(val.value, exp)

    def test_reverse_empty(self):
        """Reversing an empty list should not crash."""
        self.lib.list_reverse(self.lst)
        self.assertEqual(self.lib.list_size(self.lst), 0)

    def test_reverse_single_element(self):
        """Reversing a single-element list should be a no-op."""
        self.lib.list_insert_head(self.lst, 7)
        self.lib.list_reverse(self.lst)
        val = ctypes.c_int()
        self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(val.value, 7)

    def test_large_list(self):
        """Test with a larger number of elements."""
        n = 1000
        for i in range(n):
            self.lib.list_insert_tail(self.lst, i)
        self.assertEqual(self.lib.list_size(self.lst), n)

        # Verify first and last
        val = ctypes.c_int()
        self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(val.value, 0)
        self.lib.list_get(self.lst, n - 1, ctypes.byref(val))
        self.assertEqual(val.value, n - 1)

    def test_delete_head(self):
        """Deleting the head element works correctly."""
        self.lib.list_insert_tail(self.lst, 1)
        self.lib.list_insert_tail(self.lst, 2)
        ret = self.lib.list_delete(self.lst, 1)
        self.assertEqual(ret, 0)
        self.assertEqual(self.lib.list_size(self.lst), 1)

        val = ctypes.c_int()
        self.lib.list_get(self.lst, 0, ctypes.byref(val))
        self.assertEqual(val.value, 2)


if __name__ == "__main__":
    print("=" * 60)
    print("Linked List Automated Test Suite")
    print("=" * 60)

    # Step 1: Compile the C library
    compile_library()
    print()

    # Step 2: Run the tests
    unittest.main(verbosity=2)
