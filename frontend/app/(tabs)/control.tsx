import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Control() {
  const router = useRouter();
  const [automations, setAutomations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [user, setUser] = useState<any>(null);

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
      const response = await fetch(`${API_URL}/api/automations`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAutomations(data.automations);
      }
    } catch (error) {
      console.error('Load automations error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const toggleAutomation = async (automationId: string, currentState: boolean) => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(
        `${API_URL}/api/automations/${automationId}/toggle?enabled=${!currentState}`,
        {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        // Update local state
        setAutomations(
          automations.map((auto) =>
            auto.automation_id === automationId
              ? { ...auto, enabled: !currentState }
              : auto
          )
        );
      }
    } catch (error) {
      console.error('Toggle automation error:', error);
      Alert.alert('Error', 'Failed to update automation');
    }
  };

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await AsyncStorage.clear();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
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
        <Text style={styles.headerTitle}>Control Center</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.warningCard}>
          <Ionicons name="shield-checkmark" size={32} color="#34C759" />
          <Text style={styles.warningTitle}>You're Always in Control</Text>
          <Text style={styles.warningText}>
            TOMI only acts with your explicit permission. You can enable or disable any automation at any time.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Automation Rules</Text>
          {automations.length > 0 ? (
            automations.map((automation) => (
              <View key={automation.automation_id} style={styles.automationCard}>
                <View style={styles.automationHeader}>
                  <View style={styles.automationInfo}>
                    <Text style={styles.automationTitle}>
                      {automation.action_type.replace('_', ' ')}
                    </Text>
                    <Text style={styles.automationMeta}>
                      {automation.requires_approval ? 'Requires approval' : 'Fully automated'}
                    </Text>
                  </View>
                  <Switch
                    value={automation.enabled}
                    onValueChange={() =>
                      toggleAutomation(automation.automation_id, automation.enabled)
                    }
                    trackColor={{ false: '#E5E5E5', true: '#34C759' }}
                    thumbColor="#fff"
                  />
                </View>
                
                {automation.enabled && (
                  <View style={styles.activeIndicator}>
                    <Ionicons name="checkmark-circle" size={16} color="#34C759" />
                    <Text style={styles.activeText}>Active</Text>
                  </View>
                )}
              </View>
            ))
          ) : (
            <View style={styles.emptyAutomations}>
              <Ionicons name="construct-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>
                No automations yet. TOMI will suggest automation opportunities as it learns your patterns.
              </Text>
            </View>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account & Settings</Text>
          
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="person-outline" size={24} color="#007AFF" />
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Profile</Text>
                <Text style={styles.settingSubtitle}>{user?.name || 'Owner'}</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="business-outline" size={24} color="#007AFF" />
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Business Settings</Text>
                <Text style={styles.settingSubtitle}>Update business details</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="document-text-outline" size={24} color="#007AFF" />
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Knowledge Base</Text>
                <Text style={styles.settingSubtitle}>Manage uploaded documents</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="notifications-outline" size={24} color="#007AFF" />
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Notifications</Text>
                <Text style={styles.settingSubtitle}>Configure alerts</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Ionicons name="card-outline" size={24} color="#007AFF" />
              <View style={styles.settingInfo}>
                <Text style={styles.settingTitle}>Subscription</Text>
                <Text style={styles.settingSubtitle}>Manage your plan</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.settingItem} onPress={handleLogout}>
            <View style={styles.settingLeft}>
              <Ionicons name="log-out-outline" size={24} color="#FF3B30" />
              <View style={styles.settingInfo}>
                <Text style={[styles.settingTitle, { color: '#FF3B30' }]}>Logout</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#999" />
          </TouchableOpacity>
        </View>

        <View style={styles.versionInfo}>
          <Text style={styles.versionText}>TOMI v1.0.0</Text>
          <Text style={styles.versionText}>The Owner Mind</Text>
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
  warningCard: {
    backgroundColor: '#F0FFF4',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 24,
  },
  warningTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginTop: 12,
    marginBottom: 8,
  },
  warningText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    lineHeight: 20,
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
  automationCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  automationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  automationInfo: {
    flex: 1,
  },
  automationTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    textTransform: 'capitalize',
    marginBottom: 4,
  },
  automationMeta: {
    fontSize: 12,
    color: '#666',
  },
  activeIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
  },
  activeText: {
    fontSize: 12,
    color: '#34C759',
    fontWeight: '600',
  },
  emptyAutomations: {
    alignItems: 'center',
    padding: 32,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 12,
    lineHeight: 20,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 1,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  settingInfo: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#000',
  },
  settingSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  versionInfo: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  versionText: {
    fontSize: 12,
    color: '#999',
  },
});