/**
 * linked_list.c - Implementation of a basic singly linked list in C
 */

#include "linked_list.h"
#include <stdio.h>
#include <stdlib.h>

LinkedList *list_create(void) {
    LinkedList *list = (LinkedList *)malloc(sizeof(LinkedList));
    if (list == NULL) {
        return NULL;
    }
    list->head = NULL;
    list->size = 0;
    return list;
}

void list_destroy(LinkedList *list) {
    if (list == NULL) {
        return;
    }
    Node *current = list->head;
    while (current != NULL) {
        Node *next = current->next;
        free(current);
        current = next;
    }
    free(list);
}

static Node *create_node(int data) {
    Node *node = (Node *)malloc(sizeof(Node));
    if (node == NULL) {
        return NULL;
    }
    node->data = data;
    node->next = NULL;
    return node;
}

int list_insert_head(LinkedList *list, int data) {
    if (list == NULL) {
        return -1;
    }
    Node *node = create_node(data);
    if (node == NULL) {
        return -1;
    }
    node->next = list->head;
    list->head = node;
    list->size++;
    return 0;
}

int list_insert_tail(LinkedList *list, int data) {
    if (list == NULL) {
        return -1;
    }
    Node *node = create_node(data);
    if (node == NULL) {
        return -1;
    }
    if (list->head == NULL) {
        list->head = node;
    } else {
        Node *current = list->head;
        while (current->next != NULL) {
            current = current->next;
        }
        current->next = node;
    }
    list->size++;
    return 0;
}

int list_insert_at(LinkedList *list, size_t index, int data) {
    if (list == NULL || index > list->size) {
        return -1;
    }
    if (index == 0) {
        return list_insert_head(list, data);
    }
    Node *node = create_node(data);
    if (node == NULL) {
        return -1;
    }
    Node *current = list->head;
    for (size_t i = 0; i < index - 1; i++) {
        current = current->next;
    }
    node->next = current->next;
    current->next = node;
    list->size++;
    return 0;
}

int list_delete(LinkedList *list, int data) {
    if (list == NULL || list->head == NULL) {
        return -1;
    }
    /* Special case: head contains the value */
    if (list->head->data == data) {
        Node *to_delete = list->head;
        list->head = list->head->next;
        free(to_delete);
        list->size--;
        return 0;
    }
    Node *current = list->head;
    while (current->next != NULL) {
        if (current->next->data == data) {
            Node *to_delete = current->next;
            current->next = to_delete->next;
            free(to_delete);
            list->size--;
            return 0;
        }
        current = current->next;
    }
    return -1; /* Value not found */
}

int list_delete_at(LinkedList *list, size_t index) {
    if (list == NULL || index >= list->size) {
        return -1;
    }
    if (index == 0) {
        Node *to_delete = list->head;
        list->head = list->head->next;
        free(to_delete);
        list->size--;
        return 0;
    }
    Node *current = list->head;
    for (size_t i = 0; i < index - 1; i++) {
        current = current->next;
    }
    Node *to_delete = current->next;
    current->next = to_delete->next;
    free(to_delete);
    list->size--;
    return 0;
}

Node *list_search(const LinkedList *list, int data) {
    if (list == NULL) {
        return NULL;
    }
    Node *current = list->head;
    while (current != NULL) {
        if (current->data == data) {
            return current;
        }
        current = current->next;
    }
    return NULL;
}

int list_get(const LinkedList *list, size_t index, int *out_data) {
    if (list == NULL || index >= list->size || out_data == NULL) {
        return -1;
    }
    Node *current = list->head;
    for (size_t i = 0; i < index; i++) {
        current = current->next;
    }
    *out_data = current->data;
    return 0;
}

size_t list_size(const LinkedList *list) {
    if (list == NULL) {
        return 0;
    }
    return list->size;
}

int list_is_empty(const LinkedList *list) {
    if (list == NULL) {
        return 1;
    }
    return list->size == 0 ? 1 : 0;
}

void list_reverse(LinkedList *list) {
    if (list == NULL || list->head == NULL) {
        return;
    }
    Node *prev = NULL;
    Node *current = list->head;
    Node *next = NULL;
    while (current != NULL) {
        next = current->next;
        current->next = prev;
        prev = current;
        current = next;
    }
    list->head = prev;
}

void list_print(const LinkedList *list) {
    if (list == NULL) {
        printf("(null list)\n");
        return;
    }
    printf("[");
    Node *current = list->head;
    while (current != NULL) {
        printf("%d", current->data);
        if (current->next != NULL) {
            printf(" -> ");
        }
        current = current->next;
    }
    printf("] (size: %zu)\n", list->size);
}
