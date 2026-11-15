#include "Engine.h"
#include <cassert>
#include <iostream>

int main() {
    assert(SHA256::hash("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    assert(SHA256::hash("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    assert(TextNormalizer::normalize("  HELLO   WORLD. ") == "hello world.");
    const std::string input = "1. Explain:\n(a) Stack\n(i) Push\n(ii) Pop\n(b) Queue\n(i) Enqueue\n";
    auto qs = QuestionParser{}.parse(input);
    assert(qs.size() == 6);
    assert(qs[0].number == "1");
    assert(qs[1].number == "1(a)");
    assert(qs[2].number == "1(a)(i)");
    assert(qs[3].number == "1(a)(ii)");
    assert(qs[4].number == "1(b)");
    assert(qs[5].number == "1(b)(i)");
    std::cout << "All C++ engine tests passed.\n";
}
