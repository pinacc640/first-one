/**
 * linked_list.h - A basic singly linked list module in C
 *
 * Provides a generic integer linked list with common operations:
 * create, insert, delete, search, print, and destroy.
 */

#ifndef LINKED_LIST_H
#define LINKED_LIST_H

#include <stddef.h>

/** Node structure for the singly linked list */
typedef struct Node {
    int data;
    struct Node *next;
} Node;

/** Linked list structure with head pointer and size tracking */
typedef struct LinkedList {
    Node *head;
    size_t size;
} LinkedList;

/**
 * Create a new empty linked list.
 * @return Pointer to the newly created list, or NULL on failure.
 */
LinkedList *list_create(void);

/**
 * Destroy the linked list and free all memory.
 * @param list Pointer to the list to destroy.
 */
void list_destroy(LinkedList *list);

/**
 * Insert a value at the head of the list.
 * @param list Pointer to the list.
 * @param data The integer value to insert.
 * @return 0 on success, -1 on failure.
 */
int list_insert_head(LinkedList *list, int data);

/**
 * Insert a value at the tail of the list.
 * @param list Pointer to the list.
 * @param data The integer value to insert.
 * @return 0 on success, -1 on failure.
 */
int list_insert_tail(LinkedList *list, int data);

/**
 * Insert a value at a specific index (0-based).
 * @param list Pointer to the list.
 * @param index The position to insert at.
 * @param data The integer value to insert.
 * @return 0 on success, -1 on failure (invalid index or allocation error).
 */
int list_insert_at(LinkedList *list, size_t index, int data);

/**
 * Delete the first occurrence of a value from the list.
 * @param list Pointer to the list.
 * @param data The value to delete.
 * @return 0 on success, -1 if value not found.
 */
int list_delete(LinkedList *list, int data);

/**
 * Delete the node at a specific index.
 * @param list Pointer to the list.
 * @param index The position to delete.
 * @return 0 on success, -1 on failure (invalid index).
 */
int list_delete_at(LinkedList *list, size_t index);

/**
 * Search for a value in the list.
 * @param list Pointer to the list.
 * @param data The value to search for.
 * @return Pointer to the node containing the value, or NULL if not found.
 */
Node *list_search(const LinkedList *list, int data);

/**
 * Get the value at a specific index.
 * @param list Pointer to the list.
 * @param index The position to retrieve.
 * @param out_data Pointer to store the retrieved value.
 * @return 0 on success, -1 on failure (invalid index).
 */
int list_get(const LinkedList *list, size_t index, int *out_data);

/**
 * Get the current size of the list.
 * @param list Pointer to the list.
 * @return The number of elements in the list.
 */
size_t list_size(const LinkedList *list);

/**
 * Check if the list is empty.
 * @param list Pointer to the list.
 * @return 1 if empty, 0 otherwise.
 */
int list_is_empty(const LinkedList *list);

/**
 * Reverse the linked list in place.
 * @param list Pointer to the list.
 */
void list_reverse(LinkedList *list);

/**
 * Print all elements in the list to stdout.
 * @param list Pointer to the list.
 */
void list_print(const LinkedList *list);

#endif /* LINKED_LIST_H */
