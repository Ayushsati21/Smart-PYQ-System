#include <iostream>
#include <vector>
#include <string>
using namespace std;

class Question {
public:
    int id;
    string text, subject, term;
    int year;

    Question(int i, string t, string s, int y, string tr) {
        id = i;
        text = t;
        subject = s;
        year = y;
        term = tr;
    }

    void display() {
        cout << "\nID: " << id;
        cout << "\nQuestion: " << text;
        cout << "\nSubject: " << subject;
        cout << "\nYear: " << year;
        cout << "\nTerm: " << term << "\n";
    }
};

int main() {
    vector<Question> questions;

    questions.emplace_back(1, "What is a stack?", "DSA", 2024, "End Term");
    questions.emplace_back(2, "Explain linked list.", "DSA", 2024, "End Term");
    questions.emplace_back(3, "What is a queue?", "DSA", 2023, "Mid Term");

    cout << "SMART PYQ SYSTEM\n";
    cout << "\nAll Questions:\n";

    for (Question &q : questions) {
        q.display();
    }

    int searchYear;
    cout << "\nEnter year to search: ";
    cin >> searchYear;

    bool found = false;

    for (Question &q : questions) {
        if (q.year == searchYear) {
            q.display();
            found = true;
        }
    }

    if (!found) {
        cout << "No questions found for this year.\n";
    }

    cout << "\nTotal questions: " << questions.size() << endl;

    return 0;
}