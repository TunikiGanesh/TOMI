import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [business, setBusiness] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const userStr = await AsyncStorage.getItem('user');
      if (userStr) {
        setUser(JSON.parse(userStr));
      }

      const token = await AsyncStorage.getItem('auth_token');
      
      // Load business
      const businessRes = await fetch(`${API_URL}/api/business`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (businessRes.ok) {
        const businessData = await businessRes.json();
        setBusiness(businessData);
      }

      // Load documents
      const docsRes = await fetch(`${API_URL}/api/documents`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocuments(docsData.documents);
      }
    } catch (error) {
      console.error('Load data error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleLogout = async () => {
    await AsyncStorage.clear();
    router.replace('/(auth)/login');
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Welcome back,</Text>
            <Text style={styles.userName}>{user?.name || 'Owner'}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
            <Ionicons name="log-out-outline" size={24} color="#FF3B30" />
          </TouchableOpacity>
        </View>

        {business && (
          <View style={styles.businessCard}>
            <View style={styles.businessHeader}>
              <View style={styles.businessIcon}>
                <Ionicons name="business" size={24} color="#007AFF" />
              </View>
              <View style={styles.businessInfo}>
                <Text style={styles.businessName}>{business.name}</Text>
                <Text style={styles.businessType}>{business.business_type}</Text>
              </View>
            </View>
            <View style={styles.businessStats}>
              <View style={styles.stat}>
                <Text style={styles.statValue}>{documents.length}</Text>
                <Text style={styles.statLabel}>Documents</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.stat}>
                <Text style={styles.statValue}>{business.team_size}</Text>
                <Text style={styles.statLabel}>Team Size</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.stat}>
                <Text style={styles.statValue}>0</Text>
                <Text style={styles.statLabel}>Decisions</Text>
              </View>
            </View>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Knowledge Base Status</Text>
          <View style={styles.knowledgeCard}>
            <Ionicons name="library" size={32} color="#34C759" />
            <Text style={styles.knowledgeTitle}>Learning from {documents.length} documents</Text>
            <Text style={styles.knowledgeDescription}>
              TOMI has processed your business documents and is ready to assist with decisions
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionGrid}>
            <TouchableOpacity 
              style={[styles.actionCard, styles.primaryAction]}
              onPress={() => router.push('/chatbot')}
            >
              <Ionicons name="sparkles" size={32} color="#fff" />
              <Text style={[styles.actionText, styles.primaryActionText]}>Ask TOMI</Text>
              <Text style={styles.actionSubtext}>AI Assistant</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.actionCard}
              onPress={() => router.push('/ai-demo')}
            >
              <Ionicons name="chatbubbles" size={32} color="#007AFF" />
              <Text style={styles.actionText}>AI Demo</Text>
            </TouchableOpacity>
          </View>
          
          {/* Enterprise Features */}
          <View style={styles.enterpriseGrid}>
            <TouchableOpacity style={styles.enterpriseCard}>
              <View style={[styles.enterpriseIcon, { backgroundColor: '#E8F5E9' }]}>
                <Ionicons name="calculator" size={24} color="#4CAF50" />
              </View>
              <Text style={styles.enterpriseText}>Accounting</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.enterpriseCard}>
              <View style={[styles.enterpriseIcon, { backgroundColor: '#E3F2FD' }]}>
                <Ionicons name="people" size={24} color="#2196F3" />
              </View>
              <Text style={styles.enterpriseText}>Payroll</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.enterpriseCard}>
              <View style={[styles.enterpriseIcon, { backgroundColor: '#FFF3E0' }]}>
                <Ionicons name="storefront" size={24} color="#FF9800" />
              </View>
              <Text style={styles.enterpriseText}>Vendors</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.enterpriseCard}>
              <View style={[styles.enterpriseIcon, { backgroundColor: '#F3E5F5' }]}>
                <Ionicons name="git-branch" size={24} color="#9C27B0" />
              </View>
              <Text style={styles.enterpriseText}>Branches</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Data & Security</Text>
          <View style={styles.dataGrid}>
            <TouchableOpacity style={styles.dataCard}>
              <Ionicons name="download-outline" size={24} color="#007AFF" />
              <Text style={styles.dataCardText}>Export Data</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.dataCard}>
              <Ionicons name="cloud-download-outline" size={24} color="#34C759" />
              <Text style={styles.dataCardText}>Backup</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.dataCard}>
              <Ionicons name="shield-checkmark-outline" size={24} color="#FF9500" />
              <Text style={styles.dataCardText}>Audit Logs</Text>
            </TouchableOpacity>
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
  scrollContent: {
    padding: 16,
    paddingTop: 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  greeting: {
    fontSize: 16,
    color: '#666',
  },
  userName: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
  },
  logoutButton: {
    padding: 8,
  },
  businessCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  businessHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  businessIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#F0F7FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  businessInfo: {
    flex: 1,
  },
  businessName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#000',
  },
  businessType: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  businessStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
  },
  stat: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    backgroundColor: '#E5E5E5',
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
  knowledgeCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  knowledgeTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginTop: 12,
  },
  knowledgeDescription: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  actionGrid: {
    flexDirection: 'row',
    gap: 12,
  },
  actionCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  primaryAction: {
    backgroundColor: '#007AFF',
  },
  primaryActionText: {
    color: '#fff',
  },
  actionText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginTop: 8,
    textAlign: 'center',
  },
  actionSubtext: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 2,
  },
  enterpriseGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
    gap: 8,
  },
  enterpriseCard: {
    width: '48%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    gap: 10,
  },
  enterpriseIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  enterpriseText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  dataGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  dataCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    gap: 8,
  },
  dataCardText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#333',
    textAlign: 'center',
  },
  comingSoonSection: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    marginTop: 8,
  },
  comingSoonTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#000',
    marginTop: 16,
  },
  comingSoonText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
});