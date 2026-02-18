import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Message {
  message_id: string;
  sender: string;
  content: string;
  timestamp: string;
}

export default function ConversationDetail() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const scrollViewRef = useRef<ScrollView>(null);
  
  const [conversation, setConversation] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [replyText, setReplyText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const [loadingAI, setLoadingAI] = useState(false);

  useEffect(() => {
    loadConversation();
  }, [id]);

  const loadConversation = async () => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(`${API_URL}/api/conversations/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setConversation(data);
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Load conversation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAISuggestion = async () => {
    if (messages.length === 0) return;

    const lastCustomerMessage = [...messages]
      .reverse()
      .find((m) => m.sender === 'customer');

    if (!lastCustomerMessage) return;

    setLoadingAI(true);
    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(`${API_URL}/api/ai/suggest-reply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: lastCustomerMessage.content,
          conversation_id: id,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAiSuggestion(data.suggested_reply);
      } else {
        Alert.alert('Error', 'Failed to generate AI suggestion');
      }
    } catch (error) {
      console.error('AI suggestion error:', error);
    } finally {
      setLoadingAI(false);
    }
  };

  const useAISuggestion = () => {
    setReplyText(aiSuggestion);
    setAiSuggestion('');
  };

  const sendMessage = async () => {
    if (!replyText.trim()) return;

    setSending(true);
    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(`${API_URL}/api/conversations/${id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: replyText,
          sender: 'owner',
        }),
      });

      if (response.ok) {
        const newMessage = await response.json();
        setMessages([...messages, newMessage]);
        setReplyText('');
        setAiSuggestion('');
        
        // Scroll to bottom
        setTimeout(() => {
          scrollViewRef.current?.scrollToEnd({ animated: true });
        }, 100);
      } else {
        Alert.alert('Error', 'Failed to send message');
      }
    } catch (error) {
      console.error('Send message error:', error);
      Alert.alert('Error', 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!conversation) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style="dark" />
        <Text>Conversation not found</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      <StatusBar style="dark" />
      
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>
            {conversation.contact_name || conversation.contact_info}
          </Text>
          <Text style={styles.headerSubtitle}>{conversation.channel.toUpperCase()}</Text>
        </View>
        <TouchableOpacity onPress={getAISuggestion} style={styles.aiButton}>
          <Ionicons name="sparkles" size={24} color="#007AFF" />
        </TouchableOpacity>
      </View>

      <ScrollView
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={styles.messagesContent}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((message) => (
          <View
            key={message.message_id}
            style={[
              styles.messageBubble,
              message.sender === 'owner' ? styles.ownerMessage : styles.customerMessage,
            ]}
          >
            <Text
              style={[
                styles.messageText,
                message.sender === 'owner' && styles.ownerMessageText,
              ]}
            >
              {message.content}
            </Text>
            <Text
              style={[
                styles.messageTime,
                message.sender === 'owner' && styles.ownerMessageTime,
              ]}
            >
              {formatTime(message.timestamp)}
            </Text>
          </View>
        ))}

        {loadingAI && (
          <View style={styles.aiLoadingBubble}>
            <ActivityIndicator size="small" color="#007AFF" />
            <Text style={styles.aiLoadingText}>Generating AI suggestion...</Text>
          </View>
        )}
      </ScrollView>

      {aiSuggestion && (
        <View style={styles.aiSuggestionContainer}>
          <View style={styles.aiSuggestionHeader}>
            <Ionicons name="sparkles" size={16} color="#007AFF" />
            <Text style={styles.aiSuggestionTitle}>AI Suggestion</Text>
            <TouchableOpacity
              onPress={() => setAiSuggestion('')}
              style={styles.dismissButton}
            >
              <Ionicons name="close" size={16} color="#666" />
            </TouchableOpacity>
          </View>
          <Text style={styles.aiSuggestionText}>{aiSuggestion}</Text>
          <TouchableOpacity
            style={styles.useButton}
            onPress={useAISuggestion}
          >
            <Text style={styles.useButtonText}>Use This Reply</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="Type your reply..."
          value={replyText}
          onChangeText={setReplyText}
          multiline
          maxLength={1000}
        />
        <TouchableOpacity
          style={[styles.sendButton, (!replyText.trim() || sending) && styles.sendButtonDisabled]}
          onPress={sendMessage}
          disabled={!replyText.trim() || sending}
        >
          {sending ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons name="send" size={20} color="#fff" />
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    paddingTop: 60,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  backButton: {
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  aiButton: {
    padding: 8,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 8,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 12,
  },
  customerMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#fff',
  },
  ownerMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#007AFF',
  },
  messageText: {
    fontSize: 15,
    color: '#000',
    lineHeight: 20,
  },
  ownerMessageText: {
    color: '#fff',
  },
  messageTime: {
    fontSize: 11,
    color: '#999',
    marginTop: 4,
  },
  ownerMessageTime: {
    color: '#E5F1FF',
  },
  aiLoadingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#F0F7FF',
    borderRadius: 16,
    alignSelf: 'center',
    gap: 8,
  },
  aiLoadingText: {
    fontSize: 14,
    color: '#007AFF',
  },
  aiSuggestionContainer: {
    backgroundColor: '#F0F7FF',
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
    padding: 16,
  },
  aiSuggestionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 6,
  },
  aiSuggestionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
    flex: 1,
  },
  dismissButton: {
    padding: 4,
  },
  aiSuggestionText: {
    fontSize: 14,
    color: '#000',
    lineHeight: 20,
    marginBottom: 12,
  },
  useButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  useButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
    gap: 12,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 100,
    backgroundColor: '#F5F5F5',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
});
