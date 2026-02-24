import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Linking from 'expo-linking';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [status, setStatus] = useState('Processing...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleAuthCallback();
  }, []);

  const handleAuthCallback = async () => {
    try {
      let sessionId: string | null = null;

      // Try to get session_id from different sources
      
      // 1. From URL params (deep link)
      if (params.session_id) {
        sessionId = Array.isArray(params.session_id) ? params.session_id[0] : params.session_id;
      }
      
      // 2. From URL hash (web)
      if (!sessionId && Platform.OS === 'web' && typeof window !== 'undefined') {
        const hash = window.location.hash;
        const match = hash.match(/session_id=([^&]+)/);
        if (match) {
          sessionId = match[1];
        }
      }
      
      // 3. From initial URL (mobile deep link)
      if (!sessionId) {
        const initialUrl = await Linking.getInitialURL();
        if (initialUrl) {
          const match = initialUrl.match(/session_id=([^&]+)/);
          if (match) {
            sessionId = match[1];
          }
        }
      }

      if (!sessionId) {
        setError('No session ID found. Please try signing in again.');
        setStatus('Authentication failed');
        setTimeout(() => router.replace('/(auth)/login'), 3000);
        return;
      }

      setStatus('Verifying session...');

      // Call the backend to exchange session_id for auth token
      const response = await fetch(`${API_URL}/api/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      });

      const data = await response.json();

      if (response.ok && data.token) {
        setStatus('Sign in successful!');
        
        // Store the auth token
        await AsyncStorage.setItem('auth_token', data.token);
        
        // Store user info if available
        if (data.user) {
          await AsyncStorage.setItem('user', JSON.stringify(data.user));
        }

        // Navigate based on onboarding status
        setTimeout(() => {
          if (data.user && !data.user.onboarding_completed) {
            router.replace('/(auth)/business-setup');
          } else {
            router.replace('/(tabs)/home');
          }
        }, 1000);
      } else {
        setError(data.detail || 'Failed to verify Google sign-in');
        setStatus('Authentication failed');
        setTimeout(() => router.replace('/(auth)/login'), 3000);
      }
    } catch (err) {
      console.error('Auth callback error:', err);
      setError('An error occurred during authentication');
      setStatus('Authentication failed');
      setTimeout(() => router.replace('/(auth)/login'), 3000);
    }
  };

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#007AFF" />
      <Text style={styles.status}>{status}</Text>
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  status: {
    marginTop: 20,
    fontSize: 18,
    color: '#333',
    textAlign: 'center',
  },
  error: {
    marginTop: 16,
    fontSize: 14,
    color: '#EA4335',
    textAlign: 'center',
  },
});
