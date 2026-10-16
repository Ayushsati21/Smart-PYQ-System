
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cstdlib>
using namespace std;

int main() {
    int yearChoice, semChoice, subjectChoice, examChoice, choice;
    int paperYear, semester;
    string subject, code, exam, path;
    vector<string> subjects;
    vector<int> years;

    cout << "===== SMART PYQ SYSTEM =====\n";
    cout << "1. First Year\n";
    cout << "2. Second Year\n";
    cout << "3. Third Year\n";
    cout << "4. Fourth Year\n";
    cout << "Choose year: ";
    cin >> yearChoice;

    if (yearChoice < 1 || yearChoice > 4) {
        cout << "Invalid choice.\n";
        return 0;
    }

    cout << "\n1. Semester " << (yearChoice - 1) * 2 + 1 << "\n";
    cout << "2. Semester " << (yearChoice - 1) * 2 + 2 << "\n";
    cout << "Choose semester: ";
    cin >> semChoice;

    if (semChoice < 1 || semChoice > 2) {
        cout << "Invalid choice.\n";
        return 0;
    }

    semester = (yearChoice - 1) * 2 + semChoice;

    if (yearChoice == 1) {
        subjects = {
            "Engineering Maths",
            "Engineering Physics",
            "Basic Electrical Engineering",
            "Basic Electronics Engineering"
        };
    }
    else if (semester == 3) {
        subjects = {"Data Structures", "C++", "Career Skills"};
    }
    else if (semester == 4) {
        subjects = {"Java", "DAA"};
    }
    else {
        cout << "Subjects for this year are not added yet.\n";
        return 0;
    }

    cout << "\nChoose Subject:\n";
    for (int i = 0; i < subjects.size(); i++)
        cout << i + 1 << ". " << subjects[i] << "\n";

    cout << "Enter choice: ";
    cin >> subjectChoice;

    if (subjectChoice < 1 || subjectChoice > subjects.size()) {
        cout << "Invalid subject choice.\n";
        return 0;
    }

    subject = subjects[subjectChoice - 1];

    if (subject == "Data Structures")
        code = "DSA";
    else if (subject == "C++")
        code = "CPP";
    else if (subject == "Career Skills")
        code = "Career_Skills";
    else if (subject == "Engineering Maths")
        code = "Maths";
    else if (subject == "Engineering Physics")
        code = "Physics";
    else if (subject == "Basic Electrical Engineering")
        code = "BEE";
    else if (subject == "Basic Electronics Engineering")
        code = "BEC";
    else
        code = subject;

    cout << "\n1. Mid Term\n";
    cout << "2. End Term\n";
    cout << "Choose exam type: ";
    cin >> examChoice;

    if (examChoice == 1)
        exam = "Mid";
    else if (examChoice == 2)
        exam = "End";
    else {
        cout << "Invalid exam choice.\n";
        return 0;
    }

    if (subject == "Data Structures") {
        years = {2017, 2018, 2019};
    }
    else if (subject == "C++") {
        if (exam == "Mid")
            years = {2018};
        else
            years = {2017, 2018};
    }
    else {
        for (int y = 2017; y <= 2026; y++)
            years.push_back(y);
    }

    cout << "\nAvailable Years:\n";
    for (int i = 0; i < years.size(); i++)
        cout << i + 1 << ". " << years[i] << "\n";

    cout << "Choose paper year: ";
    cin >> choice;

    if (choice < 1 || choice > years.size()) {
        cout << "Invalid year choice.\n";
        return 0;
    }

    paperYear = years[choice - 1];

    path = "scaned papers/" + code + "_" + exam + "_"
       + to_string(paperYear) + ".pdf";

    ifstream file(path);

    if (!file) {
        cout << "\nQuestion paper not found!\n";
        cout << "Expected location:\n" << path << "\n";
        cout << "Check the folder name and PDF filename.\n";
        return 0;
    }

    file.close();

    cout << "\nOpening question paper...\n";

    string command = "open \"" + path + "\"";
    int result = system(command.c_str());

    if (result != 0)
        cout << "Unable to open PDF. Please check the file.\n";

    return 0;
}
