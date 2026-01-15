import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Button, Text } from 'react-native-paper';
import { useAuthStore } from '../store/authStore';

export const HomeScreen = () => {
  const logout = useAuthStore((state) => state.logout);

  return (
    <View style={styles.container}>
      <Text variant="headlineMedium">Добро пожаловать!</Text>
      <Button mode="outlined" onPress={logout} style={{ marginTop: 20 }}>Выйти</Button>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' }
});