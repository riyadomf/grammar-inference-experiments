package main

// Unmarshal requires one complete JSON value.
import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
)

func ok(p string) int {
	b, err := os.ReadFile(p)
	if err != nil {
		panic(err)
	}
	var v interface{}
	if json.Unmarshal(b, &v) != nil {
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
