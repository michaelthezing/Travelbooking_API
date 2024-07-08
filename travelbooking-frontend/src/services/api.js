// travelbooking-frontend/src/services/api.js
import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000';

export const registerUser = (data) => axios.post(`${API_URL}/register`, data);
export const loginUser = (data) => axios.post(`${API_URL}/login`, data);
export const bookTrip = (data) => axios.post(`${API_URL}/book-trip`, data);
export const makePayment = (data) => axios.post(`${API_URL}/make-payment`, data);
export const searchFlights = (params) => axios.get(`${API_URL}/search-flights`, { params });
