#include <iostream>
#include <string>
#include <vector>
using namespace std;

class QuestionPaper {
public:
    int paperId;
    int examYear;
    string fileName;
    string subject;
    string academicYear;
    string term;

    QuestionPaper(int id, int year, string file, string sub,
                  string academic, string t) {
        paperId = id;
        examYear = year;
        fileName = file;
        subject = sub;
        academicYear = academic;
        term = t;
    }
    void display() const {
        cout << "\nPaper ID: " << paperId;
        cout << "\nFile Name: " << fileName;
        cout << "\nSubject: " << subject;
        cout << "\nAcademic Year: " << academicYear;
        cout << "\nExam Year: " << examYear;
        cout << "\nTerm: " << term << endl;
        cout << "-----------------------------\n";
    }
};

int main() {
    vector<QuestionPaper> papers;

    QuestionPaper p1(101, 2025, "DSA.pdf",
                     "Data Structures", "2024-2025", "End Term");

    QuestionPaper p2(102, 2025, "DBMS.pdf",
                     "DBMS", "2024-2025", "Mid Term");

    QuestionPaper p3(103, 2024, "OOP.pdf",
                     "OOP", "2023-2024", "End Term");
    papers.push_back(p1);
    papers.push_back(p2);
    papers.push_back(p3);
    cout << "===== QUESTION PAPER MANAGEMENT =====\n";

    for (const QuestionPaper& p : papers) {
        p.display();
    }
    cout << "\nTotal Question Papers: " << papers.size() << endl;

    return 0;
}