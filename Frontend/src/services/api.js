import axios from 'axios';

const API_URL = "http://localhost:7060";  // Change this to your backend's API URL

export const createProject = async (name, description) => {
  try {
    const response = await axios.post(`${API_URL}/projects/`, { name, description });
    return response.data;
  } catch (error) {
    console.error("There was an error creating the project!", error);
    throw error;
  }
};

export const processNextTask = async (projectId) => {
  try {
    const response = await axios.post(`${API_URL}/projects/${projectId}/next-task`);
    return response.data;
  } catch (error) {
    console.error("There was an error processing the task!", error);
    throw error;
  }
};
