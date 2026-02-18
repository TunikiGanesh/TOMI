import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const COMMUNICATION_CHANNELS = [
  { id: 'email', name: 'Email', icon: 'mail', description: 'Receive and send emails' },
  { id: 'sms', name: 'SMS', icon: 'chatbubble', description: 'Text message notifications' },
  { id: 'whatsapp', name: 'WhatsApp', icon: 'logo-whatsapp', description: 'WhatsApp Business messages' },
  { id: 'calls', name: 'Phone Calls', icon: 'call', description: 'Voice call handling' },
];

export default function CommunicationPreferences() {
  const router = useRouter();
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['email']);
  const [loading, setLoading] = useState(false);

  const toggleChannel = (channelId: string) => {
    if (selectedChannels.includes(channelId)) {
      // Must have at least one channel selected
      if (selectedChannels.length === 1) {
        Alert.alert('Error', 'You must have at least one communication channel');
        return;
      }
      setSelectedChannels(selectedChannels.filter(id => id !== channelId));
    } else {
      setSelectedChannels([...selectedChannels, channelId]);
    }
  };

  const handleContinue = async () => {
    setLoading(true);
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      const response = await fetch(`${API_URL}/api/business/communication-preferences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          channels: selectedChannels,
        }),
      });

      if (response.ok) {
        // Navigate to knowledge import
        router.push('/(auth)/knowledge-import');
      } else {
        const error = await response.json();
        Alert.alert('Error', error.detail || 'Failed to save preferences');
      }
    } catch (error) {
      console.error('Communication preferences error:', error);
      Alert.alert('Error', 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => router.back()}
            style={styles.backButton}
          >
            <Ionicons name="arrow-back" size={24} color="#000" />
          </TouchableOpacity>
          
          <View style={styles.progressContainer}>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: '66%' }]} />
            </View>
            <Text style={styles.progressText}>Step 2 of 3</Text>
          </View>
          
          <Text style={styles.title}>How do you communicate?</Text>
          <Text style={styles.subtitle}>
            Select all channels you use to interact with customers
          </Text>
        </View>

        <View style={styles.channelList}>
          {COMMUNICATION_CHANNELS.map((channel) => (
            <TouchableOpacity
              key={channel.id}
              style={[
                styles.channelCard,
                selectedChannels.includes(channel.id) && styles.channelCardSelected,
              ]}
              onPress={() => toggleChannel(channel.id)}
            >
              <View style={styles.channelLeft}>
                <View
                  style={[
                    styles.iconContainer,
                    selectedChannels.includes(channel.id) && styles.iconContainerSelected,
                  ]}
                >
                  <Ionicons
                    name={channel.icon as any}
                    size={24}
                    color={selectedChannels.includes(channel.id) ? '#fff' : '#007AFF'}
                  />
                </View>
                <View style={styles.channelInfo}>
                  <Text style={styles.channelName}>{channel.name}</Text>
                  <Text style={styles.channelDescription}>{channel.description}</Text>
                </View>
              </View>
              
              <View
                style={[
                  styles.checkbox,
                  selectedChannels.includes(channel.id) && styles.checkboxSelected,
                ]}
              >
                {selectedChannels.includes(channel.id) && (
                  <Ionicons name="checkmark" size={18} color="#fff" />
                )}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.footer}>
          <View style={styles.infoBox}>
            <Ionicons name="information-circle" size={20} color="#007AFF" />
            <Text style={styles.infoText}>
              You can configure specific credentials for each channel later in Settings
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleContinue}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={styles.buttonText}>Continue</Text>
                <Ionicons name="arrow-forward" size={20} color="#fff" />
              </>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
  },
  header: {
    marginTop: 40,
    marginBottom: 32,
  },
  backButton: {
    marginBottom: 20,
  },
  progressContainer: {
    marginBottom: 24,
  },
  progressBar: {
    height: 4,
    backgroundColor: '#E5E5E5',
    borderRadius: 2,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  progressText: {
    fontSize: 12,
    color: '#666',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  channelList: {
    marginBottom: 24,
  },
  channelCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#E5E5E5',
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  channelCardSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#F0F7FF',
  },
  channelLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#F0F7FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  iconContainerSelected: {
    backgroundColor: '#007AFF',
  },
  channelInfo: {
    flex: 1,
  },
  channelName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  channelDescription: {
    fontSize: 14,
    color: '#666',
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#ddd',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  footer: {
    marginTop: 'auto',
  },
  infoBox: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#F0F7FF',
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  button: {
    backgroundColor: '#007AFF',
    height: 50,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});