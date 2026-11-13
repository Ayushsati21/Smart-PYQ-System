/* Preview-only data. This file is intentionally separate from the API service. */
window.MOCK_DATA = {
  papers: [
    { id: 1, name: 'TCS302 Data Structures — End Term', filename: 'TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2025-11.pdf', subject: 'Data Structures', academicYear: 'Second Year', semester: 'Semester 3', examYear: 2025, term: 'End Term', questions: 8, pages: 3, uploaded: 'Today' },
    { id: 2, name: 'TCS302 Data Structures — End Term', filename: 'TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2024-11.pdf', subject: 'Data Structures', academicYear: 'Second Year', semester: 'Semester 3', examYear: 2024, term: 'End Term', questions: 7, pages: 3, uploaded: 'Yesterday' },
    { id: 3, name: 'TCS302 Data Structures — End Term', filename: 'TCS302_DataStructures_CSE_Sem3_EndTerm_Odd_2023-11.pdf', subject: 'Data Structures', academicYear: 'Second Year', semester: 'Semester 3', examYear: 2023, term: 'End Term', questions: 9, pages: 2, uploaded: '3 days ago' },
    { id: 4, name: 'TCS302 Data Structures — Mid Term', filename: 'TCS302_DataStructures_CSE_Sem3_MidTerm_Odd_2019.pdf', subject: 'Data Structures', academicYear: 'Second Year', semester: 'Semester 3', examYear: 2019, term: 'Mid Term', questions: 10, pages: 2, uploaded: 'Last week' },
    { id: 5, name: 'Object Oriented Programming — End Term', filename: 'OOP_End_2018.pdf', subject: 'OOP in C++', academicYear: 'Second Year', semester: 'Semester 3', examYear: 2018, term: 'End Term', questions: 12, pages: 4, uploaded: 'Last week' }
  ],
  questions: [
    { id: 1, number: 'Q1', text: 'Explain the concept of a stack and describe its main operations.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2025 },
    { id: 2, number: 'Q2', text: 'Write a C function to insert a node into a singly linked list.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2025 },
    { id: 3, number: 'Q3', text: 'What is a circular queue? Explain insertion and deletion operations.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2025 },
    { id: 4, number: 'Q1', text: 'Explain the concept of a stack and describe its main operations.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2024 },
    { id: 5, number: 'Q4', text: 'Write a C function to insert a node into a singly linked list.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2024 },
    { id: 6, number: 'Q2', text: 'Define a queue and explain its operations with an example.', subject: 'Data Structures', paper: 'TCS302 Data Structures — End Term', year: 2023 },
    { id: 7, number: 'Q5', text: 'Explain the concept of a stack and describe its main operations.', subject: 'Data Structures', paper: 'TCS302 Data Structures — Mid Term', year: 2019 },
    { id: 8, number: 'Q3', text: 'What is inheritance? Explain its types in C++.', subject: 'OOP in C++', paper: 'Object Oriented Programming — End Term', year: 2018 }
  ],
  repeated: [
    { text: 'Explain the concept of a stack and describe its main operations.', frequency: 3, years: [2019, 2024, 2025], subjects: ['Data Structures'], academicYears: ['Second Year'] },
    { text: 'Write a C function to insert a node into a singly linked list.', frequency: 2, years: [2024, 2025], subjects: ['Data Structures'], academicYears: ['Second Year'] },
    { text: 'Define a queue and explain its operations with an example.', frequency: 2, years: [2023, 2025], subjects: ['Data Structures'], academicYears: ['Second Year'] },
    { text: 'Explain inheritance and describe its types in C++.', frequency: 2, years: [2018, 2022], subjects: ['OOP in C++'], academicYears: ['Second Year'] }
  ]
};
