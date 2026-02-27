import React, { useState, useRef, useEffect } from 'react';
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
  SafeAreaView,
  Linking,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: {
    internal_data_found?: {
      documents: number;
      conversations: number;
      customers: number;
      finances: number;
    };
    web_searched?: boolean;
    web_results_count?: number;
    web_sources?: string[];
  };
}

export default function ChatbotScreen() {
  const router = useRouter();
  const scrollViewRef = useRef<ScrollView>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [includeWebSearch, setIncludeWebSearch] = useState(true);
  const [sessionId] = useState(() => `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`);

  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        type: 'assistant',
        content:
          "Hello! I'm TOMI, your intelligent business assistant. I can answer questions about:\n\n" +
          '- Your business data & documents\n' +
          '- Customer information\n' +
          '- Financial records\n' +
          '- Conversations history\n' +
          '- General business advice (with live web search)\n\n' +
          'Ask me anything!',
        timestamp: new Date(),
      },
    ]);
  }, []);

  const sendMessage = async () => {
    if (!inputText.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLoading(true);

    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(`${API_URL}/api/chatbot/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: userMessage.content,
          include_web_search: includeWebSearch,
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: data.answer,
          timestamp: new Date(),
          sources: data.sources,
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const errMsg = data.error || "I couldn't process your request. Please try again.";
        setMessages(prev => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: errMsg.includes('Rate limit')
              ? 'You are sending messages too fast. Please wait a moment and try again.'
              : `Sorry, ${errMsg}`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: "I'm having trouble connecting. Please check your connection and try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (message: Message) => {
    const isUser = message.type === 'user';
    return (
      <View
        key={message.id}
        data-testid={`chat-message-${message.id}`}
        style={[styles.messageContainer, isUser ? styles.userMessage : styles.assistantMessage]}
      >
        {!isUser && (
          <View style={styles.avatarContainer}>
            <Ionicons name="sparkles" size={20} color="#007AFF" />
          </View>
        )}
        <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.assistantBubble]}>
          <Text style={[styles.messageText, isUser && styles.userMessageText]}>
            {message.content}
          </Text>

          {message.sources && (
            <View style={styles.sourcesContainer}>
              <Text style={styles.sourcesTitle}>Sources:</Text>
              <View style={styles.sourcesTags}>
                {(message.sources.internal_data_found?.documents ?? 0) > 0 && (
                  <View style={styles.sourceTag} data-testid="source-tag-documents">
                    <Ionicons name="document-text" size={12} color="#666" />
                    <Text style={styles.sourceTagText}>
                      {message.sources.internal_data_found!.documents} docs
                    </Text>
                  </View>
                )}
                {(message.sources.internal_data_found?.conversations ?? 0) > 0 && (
                  <View style={styles.sourceTag} data-testid="source-tag-conversations">
                    <Ionicons name="chatbubbles" size={12} color="#666" />
                    <Text style={styles.sourceTagText}>
                      {message.sources.internal_data_found!.conversations} chats
                    </Text>
                  </View>
                )}
                {(message.sources.internal_data_found?.customers ?? 0) > 0 && (
                  <View style={styles.sourceTag} data-testid="source-tag-customers">
                    <Ionicons name="people" size={12} color="#666" />
                    <Text style={styles.sourceTagText}>
                      {message.sources.internal_data_found!.customers} customers
                    </Text>
                  </View>
                )}
                {(message.sources.internal_data_found?.finances ?? 0) > 0 && (
                  <View style={styles.sourceTag} data-testid="source-tag-finances">
                    <Ionicons name="cash" size={12} color="#666" />
                    <Text style={styles.sourceTagText}>
                      {message.sources.internal_data_found!.finances} records
                    </Text>
                  </View>
                )}
                {message.sources.web_searched && (message.sources.web_results_count ?? 0) > 0 && (
                  <View style={styles.sourceTag} data-testid="source-tag-web">
                    <Ionicons name="globe" size={12} color="#007AFF" />
                    <Text style={[styles.sourceTagText, { color: '#007AFF' }]}>
                      {message.sources.web_results_count} web results
                    </Text>
                  </View>
                )}
              </View>

              {/* Web source URLs */}
              {message.sources.web_sources && message.sources.web_sources.length > 0 && (
                <View style={styles.webSourcesList}>
                  {message.sources.web_sources.slice(0, 3).map((url, idx) => (
                    <TouchableOpacity
                      key={idx}
                      data-testid={`web-source-link-${idx}`}
                      onPress={() => Linking.openURL(url)}
                      style={styles.webSourceLink}
                    >
                      <Ionicons name="link" size={10} color="#007AFF" />
                      <Text style={styles.webSourceUrl} numberOfLines={1}>
                        {url.replace(/https?:\/\/(www\.)?/, '').split('/')[0]}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>
          )}
        </View>
      </View>
    );
  };

  const suggestedQuestions = [
    'What are my top customers?',
    'Show me recent conversations',
    "What's my financial summary?",
    'Any pending invoices?',
  ];

  return (
    <SafeAreaView style={styles.container} data-testid="chatbot-screen">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} data-testid="chatbot-back-btn">
          <Ionicons name="arrow-back" size={24} color="#000" />
        </TouchableOpacity>
        <View style={styles.headerTitleContainer}>
          <Ionicons name="sparkles" size={24} color="#007AFF" />
          <Text style={styles.headerTitle}>TOMI Assistant</Text>
        </View>
        <TouchableOpacity
          style={styles.webSearchToggle}
          onPress={() => setIncludeWebSearch(!includeWebSearch)}
          data-testid="web-search-toggle"
        >
          <Ionicons
            name={includeWebSearch ? 'globe' : 'globe-outline'}
            size={24}
            color={includeWebSearch ? '#007AFF' : '#999'}
          />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map(renderMessage)}

          {loading && (
            <View style={[styles.messageContainer, styles.assistantMessage]} data-testid="chatbot-loading">
              <View style={styles.avatarContainer}>
                <Ionicons name="sparkles" size={20} color="#007AFF" />
              </View>
              <View style={[styles.messageBubble, styles.assistantBubble]}>
                <ActivityIndicator size="small" color="#007AFF" />
                <Text style={styles.thinkingText}>Thinking...</Text>
              </View>
            </View>
          )}

          {messages.length === 1 && (
            <View style={styles.suggestionsContainer} data-testid="suggestions-container">
              <Text style={styles.suggestionsTitle}>Try asking:</Text>
              {suggestedQuestions.map((question, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionButton}
                  data-testid={`suggestion-btn-${index}`}
                  onPress={() => setInputText(question)}
                >
                  <Ionicons name="chatbubble-outline" size={16} color="#007AFF" />
                  <Text style={styles.suggestionText}>{question}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </ScrollView>

        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Ask anything about your business..."
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={1000}
            editable={!loading}
            data-testid="chatbot-input"
          />
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || loading) && styles.sendButtonDisabled]}
            onPress={sendMessage}
            disabled={!inputText.trim() || loading}
            data-testid="chatbot-send-btn"
          >
            <Ionicons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  backButton: { padding: 4 },
  headerTitleContainer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { fontSize: 18, fontWeight: '600', color: '#000' },
  webSearchToggle: { padding: 4 },
  chatContainer: { flex: 1 },
  messagesContainer: { flex: 1 },
  messagesContent: { padding: 16, paddingBottom: 20 },
  messageContainer: { flexDirection: 'row', marginBottom: 16, alignItems: 'flex-start' },
  userMessage: { justifyContent: 'flex-end' },
  assistantMessage: { justifyContent: 'flex-start' },
  avatarContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E3F2FD',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  messageBubble: { maxWidth: '80%', padding: 12, borderRadius: 16 },
  userBubble: { backgroundColor: '#007AFF', borderBottomRightRadius: 4 },
  assistantBubble: { backgroundColor: '#f0f0f0', borderBottomLeftRadius: 4 },
  messageText: { fontSize: 15, lineHeight: 22, color: '#333' },
  userMessageText: { color: '#fff' },
  thinkingText: { fontSize: 14, color: '#666', marginLeft: 8 },
  sourcesContainer: { marginTop: 12, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#ddd' },
  sourcesTitle: { fontSize: 11, color: '#666', marginBottom: 6 },
  sourcesTags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  sourceTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  sourceTagText: { fontSize: 11, color: '#666' },
  webSourcesList: { marginTop: 8, gap: 4 },
  webSourceLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 2,
  },
  webSourceUrl: { fontSize: 11, color: '#007AFF', maxWidth: 200 },
  suggestionsContainer: {
    marginTop: 16,
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
  },
  suggestionsTitle: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 12 },
  suggestionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#fff',
    borderRadius: 8,
    marginBottom: 8,
    gap: 8,
  },
  suggestionText: { fontSize: 14, color: '#007AFF' },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: '#eee',
    backgroundColor: '#fff',
  },
  input: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    paddingTop: 10,
    fontSize: 15,
    maxHeight: 100,
    marginRight: 8,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007AFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: { backgroundColor: '#ccc' },
});
