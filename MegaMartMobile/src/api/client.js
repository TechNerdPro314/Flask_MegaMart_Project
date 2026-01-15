import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

// ДЛЯ ЭМУЛЯТОРА ANDROID: http://10.0.2.2:8000/api
// ДЛЯ ТЕЛЕФОНА/IOS: http://192.168.1.X:8000/api (вставь свой IP)
const BASE_URL = Platform.OS === 'android' 
  ? 'http://10.0.2.2:8000/api' 
  : 'http://localhost:8000/api';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use(async (config) => {
  try {
    const token = await SecureStore.getItemAsync('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (error) {
    console.error("Error getting token", error);
  }
  return config;
});

export default client;