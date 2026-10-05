package main

// Require one root and no non-whitespace text outside it.
import (
	"bufio"
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
	"os"
	"strings"
)

func ok(p string) int {
	b, err := os.ReadFile(p)
	if err != nil {
		panic(err)
	}
	d := xml.NewDecoder(bytes.NewReader(b))
	depth, roots := 0, 0
	for {
		t, err := d.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return 1
		}
		switch v := t.(type) {
		case xml.StartElement:
			if depth == 0 {
				roots++
			}
			depth++
		case xml.EndElement:
			depth--
		case xml.CharData:
			if depth == 0 && strings.TrimSpace(string(v)) != "" {
				return 1
			}
		}
	}
	if roots != 1 || depth != 0 {
		return 1
	}
	return 0
}
func main() {
	f, err := os.Open(os.Args[1])
	if err != nil {
		panic(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	i := 0
	for sc.Scan() {
		fmt.Printf("%d %d\n", i, ok(sc.Text()))
		i++
	}
	if err := sc.Err(); err != nil {
		panic(err)
	}
}
