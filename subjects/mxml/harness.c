// Mini-XML document parser. Exit: 0 clean, 1 rejected, 2 harness error,
// 3 parsed with diagnostics. Diagnostics use escaped tab-separated records.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mxml.h"

#define EXIT_PARSED_CLEAN 0
#define EXIT_REJECTED     1
#define EXIT_HARNESS_ERR  2
#define EXIT_PARSED_DIAG  3

static int n_diags = 0;
// Keep embedded control bytes from splitting diagnostic records.
static void on_error(void *cbdata, const char *message)
{
  (void)cbdata;
  n_diags++;
  fputs("DIAG\t", stdout);
  for (const char *p = message ? message : "(null)"; *p; p++) {
    unsigned char c = (unsigned char)*p;
    switch (c) {
      case '\n': fputs("\\n", stdout); break;
      case '\r': fputs("\\r", stdout); break;
      case '\t': fputs("\\t", stdout); break;
      case '\\': fputs("\\\\", stdout); break;
      default:
        if (c < 0x20 || c == 0x7f)
          printf("\\x%02x", c);
        else
          fputc((int)c, stdout);
    }
  }
  fputc('\n', stdout);
}
static char *slurp(FILE *f, size_t *out_len)
{
  size_t cap = 65536, len = 0;
  char *buf = malloc(cap);
  if (!buf)
    return NULL;

  for (;;) {
    if (len + 1 >= cap) {
      size_t ncap = cap * 2;
      char *nbuf = realloc(buf, ncap);
      if (!nbuf) {
        free(buf);
        return NULL;
      }
      buf = nbuf;
      cap = ncap;
    }
    size_t n = fread(buf + len, 1, cap - len - 1, f);
    if (n == 0)
      break;
    len += n;
  }

  buf[len] = '\0';
  *out_len = len;
  return buf;
}

int main(int argc, char **argv)
{
  const char *path = NULL;
  int build_index = 0;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--index"))
      build_index = 1;
    else
      path = argv[i];
  }

  FILE *f = path ? fopen(path, "rb") : stdin;
  if (!f) {
    fprintf(stderr, "harness: cannot open %s\n", path);
    return EXIT_HARNESS_ERR;
  }

  size_t len = 0;
  char *doc = slurp(f, &len);
  if (path)
    fclose(f);
  if (!doc) {
    fprintf(stderr, "harness: out of memory reading input\n");
    return EXIT_HARNESS_ERR;
  }

  mxml_options_t *opts = mxmlOptionsNew();
  if (!opts) {
    free(doc);
    fprintf(stderr, "harness: mxmlOptionsNew failed\n");
    return EXIT_HARNESS_ERR;
  }
  mxmlOptionsSetErrorCallback(opts, on_error, NULL);
  mxml_node_t *tree = mxmlLoadString(NULL, opts, doc);

  if (tree && build_index) {
    mxml_index_t *ind = mxmlIndexNew(tree, NULL, NULL);
    if (ind)
      mxmlIndexDelete(ind);
  }

  printf("RESULT\t%s\t%d\n", tree ? "parsed" : "rejected", n_diags);
  fflush(stdout);

  int rc;
  if (tree) {
    rc = n_diags ? EXIT_PARSED_DIAG : EXIT_PARSED_CLEAN;
    mxmlDelete(tree);
  } else {
    rc = EXIT_REJECTED;
  }

  mxmlOptionsDelete(opts);
  free(doc);
  return rc;
}
