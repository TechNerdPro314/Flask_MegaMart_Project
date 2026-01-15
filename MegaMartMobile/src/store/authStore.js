import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

export const useAuthStore = create((set) => ({
  token: null,
  user: null,
  isLoading: true,

  login: async (token, user) => {
    await SecureStore.setItemAsync('auth_token', token);
    set({ token, user, isLoading: false });
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('auth_token');
    set({ token: null, user: null, isLoading: false });
  },

  loadToken: async () => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        set({ token, isLoading: false });
      } else {
        set({ token: null, isLoading: false });
      }
    } catch (e) {
      set({ token: null, isLoading: false });
    }
  },
}));