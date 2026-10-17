#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>
using namespace std;

class RepeatedQuestion
{
private:
    string question;
    int count;

public:
    RepeatedQuestion(string q, int c)
    {
        question = q;
        count = c;
    }

    string getQuestion()
    {
        return question;
    }

    int getCount()
    {
        return count;
    }
};
class FrequencyAnalyzer
{
private:
    vector<RepeatedQuestion> repeatedQuestions;

public:
    void analyze(vector<string> questions)
    {
        unordered_map<string, int> frequency;

        // Count each question using a hash map
        for (string q : questions)
        {
            frequency[q]++;
        }

        repeatedQuestions.clear();

       
        for (auto item : frequency)
        {
            if (item.second > 1)
            {
                repeatedQuestions.push_back(
                    RepeatedQuestion(item.first, item.second));
            }
        }
        sort(repeatedQuestions.begin(), repeatedQuestions.end(),
             [](RepeatedQuestion a, RepeatedQuestion b)
             {
                 return a.getCount() > b.getCount();
             });
    }

    void display()
    {
        if (repeatedQuestions.empty())
        {
            cout << "\nNo repeated questions found.\n";
            return;
        }

        cout << "\n===== REPEATED QUESTIONS =====\n";

        for (int i = 0; i < repeatedQuestions.size(); i++)
        {
            cout << i + 1 << ". "
                 << repeatedQuestions[i].getQuestion()
                 << "\n   Asked "
                 << repeatedQuestions[i].getCount()
                 << " times\n\n";
        }
    }
};

int main()
{
    int yearChoice, subjectChoice, termChoice;
    string year, subject, term;

    cout << "===== SMART PYQ SYSTEM =====\n";

    // Select academic year
    cout << "\nSelect Academic Year:\n";
    cout << "1. First Year\n";
    cout << "2. Second Year\n";
    cout << "3. Third Year\n";
    cout << "4. Fourth Year\n";
    cout << "Enter choice: ";
    cin >> yearChoice;

    switch (yearChoice)
    {
    case 1: year = "First Year"; break;
    case 2: year = "Second Year"; break;
    case 3: year = "Third Year"; break;
    case 4: year = "Fourth Year"; break;
    default:
        cout << "Invalid year choice.\n";
        return 0;
    }

    cout << "\nSelect Subject:\n";
    cout << "1. Data Structures\n";
    cout << "2. OOP in C++\n";
    cout << "3. DBMS\n";
    cout << "Enter choice: ";
    cin >> subjectChoice;

    switch (subjectChoice)
    {
    case 1: subject = "Data Structures"; break;
    case 2: subject = "OOP in C++"; break;
    case 3: subject = "DBMS"; break;
    default:
        cout << "Invalid subject choice.\n";
        return 0;
    }

    cout << "\nSelect Term:\n";
    cout << "1. Mid Term\n";
    cout << "2. End Term\n";
    cout << "Enter choice: ";
    cin >> termChoice;

    switch (termChoice)
    {
    case 1: term = "Mid Term"; break;
    case 2: term = "End Term"; break;
    default:
        cout << "Invalid term choice.\n";
        return 0;
    }

    cout << "\nSelected Details:\n";
    cout << "Year: " << year << endl;
    cout << "Subject: " << subject << endl;
    cout << "Term: " << term << endl;

    vector<string> questions = {
        "Explain the concept of a stack.",
        "What is a linked list?",
        "Explain the concept of a stack.",
        "Define a queue and explain its operations.",
        "What is a linked list?",
        "Explain the concept of a stack.",
        "Write an algorithm for binary search.",
        "Define a queue and explain its operations.",
        "What is a linked list?"
    };

    cout << "\nTotal questions available: "
         << questions.size() << endl;

    FrequencyAnalyzer analyzer;
    analyzer.analyze(questions);

    cout << "\nResults for " << year << " | "
         << subject << " | " << term << endl;

    analyzer.display();

    return 0;
}