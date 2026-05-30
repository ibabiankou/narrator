# Project Gemini: Narrator

This document provides a high-level overview of the Narrator project, its components, and instructions for getting started.

## Overview

Narrator is a web-based application for reading and listening to digital books. It consists of the following key components:

*   **Backend API (`/api`)**: A Python-based backend powered by FastAPI that manages books, and content processing. It exposes a RESTful API for the frontend to consume.
*   **Frontend Web App (`/web-app`)**: An Angular-based single-page application that provides the user interface for browsing, reading, and listening to books.
*   **Speech Generator (`/speech-generator`)**: A Python-based service that converts text from books into high-quality audio.
*   **Common Code Library (`/common-lib`)**: A Python library for sharing functionality between the Backend and Speech Generator.
*   **EPUB Library (`/epub-lib`)**: A Python library for parsing and manipulating EPUB files.

## High-level guidelines

* Do now write or run tests for frontend code. 

### Key Commands

*   **Run the Python tests**:
    ```bash
    cd api
    poetry run pytest
    cd ..
    
    cd common-lib
    poetry run pytest
    cd ..

    cd epub-lib
    poetry run pytest
    cd ..
    ```
*   **Run the backend API and dependencies in development mode**:
    ```bash
    ./compose build api && ./compose up api
    ```
*   **Run the frontend web app in development mode**:
    ```bash
    cd web-app
    npm run dev
    ```
*   **Run the speech generator and dependencies in development mode**:
    ```bash
    ./compose build speech && ./compose up speech
    ```

## Key Technologies

*   **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL
*   **Frontend**: TypeScript, Angular
*   **Speech Generation**: Python, Kokoro
*   **Containerization**: Docker, Docker Compose
