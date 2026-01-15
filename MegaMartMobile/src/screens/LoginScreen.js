import React, { useState } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Button, TextInput, Text } from 'react-native-paper';
import { useAuthStore } from '../store/authStore';
import client from '../api/client';

export const LoginScreen = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((state) => state.login);

  const handleLogin = async () => {
    if (!email || !password) return;
    setLoading(true);
    try {
      const response = await client.post('/auth/login', { email, password });
      const { access_token, user } = response.data;
      await login(access_token, user);
    } catch (error) {
      console.error(error);
      Alert.alert('Ошибка', 'Неверный логин или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text variant="headlineMedium" style={styles.title}>MegaMart Вход</Text>
      <TextInput label="Email" value={email} onChangeText={setEmail} style={styles.input} autoCapitalize="none" keyboardType="email-address"/>
      <TextInput label="Пароль" value={password} onChangeText={setPassword} secureTextEntry style={styles.input} />
      <Button mode="contained" onPress={handleLogin} loading={loading} style={styles.button}>Войти</Button>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 20, backgroundColor: '#fff' },
  title: { textAlign: 'center', marginBottom: 30, fontWeight: 'bold' },
  input: { marginBottom: 15 },
  button: { marginTop: 10 }
});