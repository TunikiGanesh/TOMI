import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter, useSegments } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Index() {
  const router = useRouter();
  const segments = useSegments();
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // Check for stored token
      const token = await AsyncStorage.getItem('auth_token');
      
      if (!token) {
        // No token, go to login
        router.replace('/(auth)/login');
        return;
      }

      // Verify token with backend
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const user = await response.json();
        
        // Check if onboarding is completed
        if (!user.onboarding_completed) {
          router.replace('/(auth)/business-setup');
        } else {
          router.replace('/(tabs)/home');
        }
      } else {
        // Invalid token
        await AsyncStorage.removeItem('auth_token');
        router.replace('/(auth)/login');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.replace('/(auth)/login');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.logoMark}>
          <Text style={styles.logoLetter}>T</Text>
        </View>
        <Text style={styles.title}>TOMI</Text>
        <Text style={styles.subtitle}>The Owner Mind</Text>
        <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoMark: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  logoLetter: {
    fontSize: 44,
    fontWeight: 'bold',
    color: '#fff',
  },
  title: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#999',
    marginBottom: 40,
  },
  loader: {
    marginTop: 20,
  },
});