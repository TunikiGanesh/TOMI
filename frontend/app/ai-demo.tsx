import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function AIDemo() {
  const router = useRouter();
  const [customerMessage, setCustomerMessage] = useState('');
  const [suggestedReply, setSuggestedReply] = useState('');
  const [loading, setLoading] = useState(false);
  const [modelUsed, setModelUsed] = useState('');
  const [analysis, setAnalysis] = useState<any>(null);

  const testMessages = [
    "Hi, what are your business hours?",
    "I'm interested in your services. Can you tell me more about pricing?",
    "I need to schedule an appointment for next week. Are you available?",
    "Do you offer any discounts for bulk orders?",
    "I had a problem with my last order. Can you help?",
  ];

  const getSuggestion = async (message?: string) => {
    const msg = message || customerMessage;
    if (!msg.trim()) {
      Alert.alert('Error', 'Please enter a message');
      return;
    }

    setLoading(true);
    setSuggestedReply('');
    setAnalysis(null);

    try {
      const token = await AsyncStorage.getItem('auth_token');

      // Get AI suggestion
      const response = await fetch(`${API_URL}/api/ai/suggest-reply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: msg }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuggestedReply(data.suggested_reply);
        setModelUsed(data.model_used);
      } else {
        const error = await response.json();
        Alert.alert('Error', error.detail || 'Failed to generate suggestion');
      }

      // Get message analysis
      const analysisResponse = await fetch(`${API_URL}/api/ai/analyze-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: msg }),
      });

      if (analysisResponse.ok) {
        const analysisData = await analysisResponse.json();
        setAnalysis(analysisData);
      }
    } catch (error) {
      console.error('AI suggestion error:', error);
      Alert.alert('Error', 'Failed to connect to AI service');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#000" />
          </TouchableOpacity>
          <Text style={styles.title}>AI Assistant Demo</Text>
          <Text style={styles.subtitle}>
            Test TOMI's AI-powered reply suggestions using your business context
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Try Example Messages</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {testMessages.map((msg, index) => (
              <TouchableOpacity
                key={index}
                style={styles.exampleChip}
                onPress={() => {
                  setCustomerMessage(msg);
                  getSuggestion(msg);
                }}
              >
                <Text style={styles.exampleText}>{msg}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Customer Message</Text>
          <TextInput
            style={styles.textArea}
            placeholder="Enter a customer message..."
            value={customerMessage}
            onChangeText={setCustomerMessage}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />
          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={() => getSuggestion()}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="sparkles" size={20} color="#fff" />
                <Text style={styles.buttonText}>Generate AI Suggestion</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {analysis && (
          <View style={styles.analysisCard}>
            <Text style={styles.cardTitle}>Message Analysis</Text>
            <View style={styles.analysisRow}>
              <View style={styles.analysisItem}>
                <Text style={styles.analysisLabel}>Intent</Text>
                <Text style={styles.analysisValue}>{analysis.intent || 'inquiry'}</Text>
              </View>
              <View style={styles.analysisItem}>
                <Text style={styles.analysisLabel}>Sentiment</Text>
                <Text style={[
                  styles.analysisValue,
                  { color: analysis.sentiment === 'positive' ? '#34C759' : '#666' }
                ]}>
                  {analysis.sentiment || 'neutral'}
                </Text>
              </View>
              <View style={styles.analysisItem}>
                <Text style={styles.analysisLabel}>Urgency</Text>
                <Text style={[
                  styles.analysisValue,
                  { color: analysis.urgency === 'high' ? '#FF3B30' : '#666' }
                ]}>
                  {analysis.urgency || 'medium'}
                </Text>
              </View>
            </View>
            {analysis.key_topics && (
              <View style={styles.topics}>
                <Text style={styles.analysisLabel}>Topics:</Text>
                <Text style={styles.analysisValue}>
                  {Array.isArray(analysis.key_topics)
                    ? analysis.key_topics.join(', ')
                    : analysis.key_topics}
                </Text>
              </View>
            )}
          </View>
        )}

        {suggestedReply && (
          <View style={styles.replyCard}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>AI Suggested Reply</Text>
              {modelUsed && (
                <View style={styles.modelBadge}>
                  <Ionicons name="hardware-chip" size={12} color="#007AFF" />
                  <Text style={styles.modelText}>{modelUsed}</Text>
                </View>
              )}
            </View>
            <View style={styles.replyContent}>
              <Text style={styles.replyText}>{suggestedReply}</Text>
            </View>
            <View style={styles.replyActions}>
              <TouchableOpacity style={styles.actionButton}>
                <Ionicons name="create-outline" size={20} color="#007AFF" />
                <Text style={styles.actionText}>Edit</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionButton}>
                <Ionicons name="copy-outline" size={20} color="#007AFF" />
                <Text style={styles.actionText}>Copy</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.actionButton, styles.sendButton]}>
                <Ionicons name="send" size={20} color="#fff" />
                <Text style={[styles.actionText, { color: '#fff' }]}>Send</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        <View style={styles.infoBox}>
          <Ionicons name="information-circle" size={20} color="#007AFF" />
          <Text style={styles.infoText}>
            TOMI analyzes your business documents to provide context-aware suggestions that match your business style and information.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollContent: {
    padding: 16,
    paddingTop: 60,
    paddingBottom: 100,
  },
  header: {
    marginBottom: 24,
  },
  backButton: {
    marginBottom: 16,
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
    lineHeight: 22,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 12,
  },
  exampleChip: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    backgroundColor: '#fff',
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E5E5E5',
  },
  exampleText: {
    fontSize: 14,
    color: '#007AFF',
  },
  textArea: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    backgroundColor: '#fff',
    minHeight: 100,
    marginBottom: 16,
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
  analysisCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E5E5E5',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  analysisRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  analysisItem: {
    flex: 1,
  },
  analysisLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  analysisValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    textTransform: 'capitalize',
  },
  topics: {
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
  },
  modelBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#F0F7FF',
    borderRadius: 12,
  },
  modelText: {
    fontSize: 10,
    color: '#007AFF',
    fontWeight: '600',
  },
  replyCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E5E5E5',
  },
  replyContent: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  replyText: {
    fontSize: 15,
    color: '#000',
    lineHeight: 22,
  },
  replyActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    gap: 8,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007AFF',
    gap: 6,
  },
  sendButton: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  actionText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  infoBox: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#F0F7FF',
    borderRadius: 8,
    gap: 8,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});
