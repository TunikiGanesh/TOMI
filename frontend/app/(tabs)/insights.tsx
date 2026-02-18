import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Insights() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [insight, setInsight] = useState('');
  const [business, setBusiness] = useState<any>(null);
  const [stats, setStats] = useState({
    conversations: 0,
    documents: 0,
    decisions: 0,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      // Load business
      const businessRes = await fetch(`${API_URL}/api/business`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (businessRes.ok) {
        setBusiness(await businessRes.json());
      }

      // Load conversations count
      const convRes = await fetch(`${API_URL}/api/conversations`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (convRes.ok) {
        const convData = await convRes.json();
        setStats((prev) => ({ ...prev, conversations: convData.count }));
      }

      // Load documents count
      const docsRes = await fetch(`${API_URL}/api/documents`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setStats((prev) => ({ ...prev, documents: docsData.count }));
      }

      // Load decisions count
      const decRes = await fetch(`${API_URL}/api/decisions`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (decRes.ok) {
        const decData = await decRes.json();
        setStats((prev) => ({ ...prev, decisions: decData.total_decisions }));
      }
    } catch (error) {
      console.error('Load insights error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Insights</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Ionicons name="chatbubbles" size={32} color="#007AFF" />
            <Text style={styles.statValue}>{stats.conversations}</Text>
            <Text style={styles.statLabel}>Conversations</Text>
          </View>

          <View style={styles.statCard}>
            <Ionicons name="document-text" size={32} color="#34C759" />
            <Text style={styles.statValue}>{stats.documents}</Text>
            <Text style={styles.statLabel}>Documents</Text>
          </View>

          <View style={styles.statCard}>
            <Ionicons name="analytics" size={32} color="#FF9500" />
            <Text style={styles.statValue}>{stats.decisions}</Text>
            <Text style={styles.statLabel}>Decisions</Text>
          </View>
        </View>

        <View style={styles.insightCard}>
          <View style={styles.insightHeader}>
            <Ionicons name="bulb" size={24} color="#FF9500" />
            <Text style={styles.insightTitle}>Business Activity Summary</Text>
          </View>
          <Text style={styles.insightText}>
            {business ? (
              `Your ${business.business_type} business "${business.name}" is currently tracking ${stats.conversations} conversations, ${stats.documents} knowledge documents, and ${stats.decisions} decisions.\n\nTOMI is learning from your interactions to provide better suggestions over time.`
            ) : (
              'Loading business insights...'
            )}
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Key Metrics</Text>
          
          <View style={styles.metricCard}>
            <View style={styles.metricHeader}>
              <Text style={styles.metricTitle}>Response Time</Text>
              <Ionicons name="time-outline" size={20} color="#007AFF" />
            </View>
            <Text style={styles.metricValue}>{'< 2 hours'}</Text>
            <Text style={styles.metricChange}>↑ 20% faster</Text>
          </View>

          <View style={styles.metricCard}>
            <View style={styles.metricHeader}>
              <Text style={styles.metricTitle}>AI Suggestions Used</Text>
              <Ionicons name="sparkles-outline" size={20} color="#34C759" />
            </View>
            <Text style={styles.metricValue}>Coming Soon</Text>
            <Text style={styles.metricDescription}>Track AI usage patterns</Text>
          </View>

          <View style={styles.metricCard}>
            <View style={styles.metricHeader}>
              <Text style={styles.metricTitle}>Automation Efficiency</Text>
              <Ionicons name="settings-outline" size={20} color="#FF9500" />
            </View>
            <Text style={styles.metricValue}>0% automated</Text>
            <Text style={styles.metricDescription}>Enable automations to track efficiency</Text>
          </View>
        </View>

        <View style={styles.tipsCard}>
          <Text style={styles.tipsTitle}>💡 Tips to Improve</Text>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#34C759" />
            <Text style={styles.tipText}>Upload more business documents for better AI context</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#34C759" />
            <Text style={styles.tipText}>Review AI suggestions to train TOMI on your style</Text>
          </View>
          <View style={styles.tipItem}>
            <Ionicons name="checkmark-circle" size={20} color="#34C759" />
            <Text style={styles.tipText}>Enable automations for repetitive tasks</Text>
          </View>
        </View>
      </ScrollView>
    </View>
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
    padding: 16,
    paddingTop: 60,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textAlign: 'center',
  },
  insightCard: {
    backgroundColor: '#FFF9E6',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  insightTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
  },
  insightText: {
    fontSize: 14,
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
  metricCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  metricHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  metricTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  metricValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#000',
    marginBottom: 4,
  },
  metricChange: {
    fontSize: 14,
    color: '#34C759',
    fontWeight: '500',
  },
  metricDescription: {
    fontSize: 12,
    color: '#999',
  },
  tipsCard: {
    backgroundColor: '#F0F7FF',
    borderRadius: 12,
    padding: 20,
  },
  tipsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    marginBottom: 16,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 12,
  },
  tipText: {
    flex: 1,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});