# Frontend - Project Management Application

This is the front-end application for the Project Management API. It provides a user interface to interact with the FastAPI backend, allowing you to create projects, assign tasks, and view results.

## Features

- **Create Projects**: Allows users to create new projects with a name and description.
- **View Project Details**: Displays the details of the project after it has been created.
- **Process Tasks**: Allows users to process the next available task for a project and view the results.
- **API Integration**: Communicates with the FastAPI backend to manage tasks and projects.

## Setup

### Prerequisites

Make sure you have the following tools installed:

- **Node.js**: Version 14.x or later (You can download it from [here](https://nodejs.org/)).
- **npm**: The Node package manager, which comes with Node.js.

### Installation

To set up the project, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd frontend
   ```

2. **Install dependencies**:
   Run the following command in the `frontend` directory to install all the required dependencies:
   ```bash
   npm install
   ```

### Environment Variables

Ensure that the backend FastAPI server is running and that the `API_URL` in `src/services/api.js` matches the URL where the FastAPI backend is accessible. By default, it is set to `http://localhost:7060`.

```js
const API_URL = "http://localhost:7060";  // Change this if your backend is hosted elsewhere
```

### Running the Application

To start the React application, run the following command:

```bash
npm start
```

This will launch the app in your default web browser at `http://localhost:3000`.

### Development

For local development, if you want to work on both the backend and frontend:

1. **Run the FastAPI backend** (ensure CORS is enabled on the backend for local development).
   In the `Backend` directory:
   ```bash
   uvicorn app:app --reload
   ```

2. **Run the React front-end**:
   In the `frontend` directory:
   ```bash
   npm start
   ```

Your application will be running at `http://localhost:3000` and will interact with the FastAPI backend running at `http://localhost:7060`.

### Build the Application for Production

When you're ready to deploy the application, you can build the optimized production version of the React app:

```bash
npm run build
```

The production-ready build will be located in the `build/` directory. You can then serve it using any static file server or host it on services like Netlify, Vercel, or GitHub Pages.

## Directory Structure

Here is the directory structure for the front-end application:

```
/public               # Static assets like index.html, images, etc.
    /index.html       # The main HTML template for the React app
    /favicon.ico      # The app's favicon
/src
    /components        # React components (e.g., forms, project display)
    /services          # API functions for interacting with FastAPI
    /App.js            # Main app component
    /index.js          # Entry point for the React app
    /styles.css        # Optional CSS file for styling the app
package.json           # Project metadata and dependencies
README.md              # Documentation for the front-end
```

## API Documentation

The front-end interacts with the following endpoints from the FastAPI backend:

### `POST /projects/`

- **Request**: Creates a new project with the given `name` and `description`.
- **Response**: Returns the newly created project, including its `id`, `name`, `description`, and `status`.

### `POST /projects/{project_id}/next-task`

- **Request**: Processes the next task for the specified `project_id`.
- **Response**: Returns the task's details, its assigned agent, and the result of processing the task.

## Contribution

Feel free to contribute to this project! If you'd like to suggest improvements or add new features, please open an issue or submit a pull request.

### Steps for Contribution:

1. Fork the repository.
2. Create a new branch for your feature/bug fix.
3. Make your changes and commit them.
4. Push your branch to your forked repository.
5. Create a pull request to the main repository.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.