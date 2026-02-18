import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Switch,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Decisions() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [patterns, setPatterns] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDecisions();
  }, []);

  const loadDecisions = async () => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      const response = await fetch(`${API_URL}/api/decisions`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setDecisions(data.decisions);
        setPatterns(data.patterns);
      }
    } catch (error) {
      console.error('Load decisions error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadDecisions();
  };

  const getPatternPercentage = (pattern: any, decision: string) => {
    if (!pattern || pattern.total === 0) return 0;
    return Math.round((pattern[decision] / pattern.total) * 100);
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
        <Text style={styles.headerTitle}>Decision Learning</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.infoCard}>
          <Ionicons name="analytics" size={32} color="#007AFF" />
          <Text style={styles.infoTitle}>Learning Your Patterns</Text>
          <Text style={styles.infoText}>
            TOMI observes your decisions and identifies patterns to suggest automation opportunities. You stay in control.
          </Text>
        </View>

        {Object.keys(patterns).length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Decision Patterns</Text>
            {Object.entries(patterns).map(([actionType, pattern]: [string, any]) => (
              <View key={actionType} style={styles.patternCard}>
                <View style={styles.patternHeader}>
                  <Text style={styles.patternTitle}>{actionType.replace('_', ' ')}</Text>
                  <Text style={styles.patternCount}>{pattern.total} decisions</Text>
                </View>
                
                <View style={styles.progressBar}>
                  <View
                    style={[
                      styles.progressFill,
                      styles.approvedFill,
                      { width: `${getPatternPercentage(pattern, 'approved')}%` }
                    ]}
                  />
                </View>
                
                <View style={styles.patternStats}>
                  <View style={styles.stat}>
                    <View style={[styles.statDot, { backgroundColor: '#34C759' }]} />
                    <Text style={styles.statText}>
                      {getPatternPercentage(pattern, 'approved')}% Approved
                    </Text>
                  </View>
                  <View style={styles.stat}>
                    <View style={[styles.statDot, { backgroundColor: '#FF3B30' }]} />
                    <Text style={styles.statText}>
                      {getPatternPercentage(pattern, 'rejected')}% Rejected
                    </Text>
                  </View>
                </View>

                {pattern.approved >= 5 && (
                  <View style={styles.suggestionBanner}>
                    <Ionicons name="bulb" size={16} color="#FF9500" />
                    <Text style={styles.suggestionText}>
                      Consistent pattern detected - automation eligible
                    </Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        )}

        {decisions.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recent Decisions ({decisions.length})</Text>
            {decisions.slice(0, 10).map((decision, index) => (
              <View key={index} style={styles.decisionCard}>
                <View style={styles.decisionHeader}>
                  <View style={styles.decisionType}>
                    <Ionicons
                      name={decision.decision === 'approved' ? 'checkmark-circle' : 'close-circle'}
                      size={20}
                      color={decision.decision === 'approved' ? '#34C759' : '#FF3B30'}
                    />
                    <Text style={styles.decisionTypeText}>{decision.action_type}</Text>
                  </View>
                  <Text style={styles.decisionDate}>
                    {new Date(decision.timestamp).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.decisionStatus}>{decision.decision}</Text>
              </View>
            ))}
          </View>
        )}

        {decisions.length === 0 && (
          <View style={styles.emptyState}>
            <Ionicons name="Analytics-outline" size={64} color="#ccc" />
            <Text style={styles.emptyTitle}>No Decisions Recorded Yet</Text>
            <Text style={styles.emptyText}>
              As you interact with customers and make decisions, TOMI will learn your patterns.
            </Text>
          </View>
        )}
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
  infoCard: {
    backgroundColor: '#F0F7FF',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 24,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginTop: 12,
    marginBottom: 8,
  },
  infoText: {
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
  patternCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  patternHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  patternTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
    textTransform: 'capitalize',
  },
  patternCount: {
    fontSize: 12,
    color: '#666',
  },
  progressBar: {
    height: 8,
    backgroundColor: '#E5E5E5',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 12,
  },
  progressFill: {
    height: '100%',
  },
  approvedFill: {
    backgroundColor: '#34C759',
  },
  patternStats: {
    flexDirection: 'row',
    gap: 16,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statText: {
    fontSize: 12,
    color: '#666',
  },
  suggestionBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF9E6',
    padding: 10,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  suggestionText: {
    fontSize: 12,
    color: '#FF9500',
    flex: 1,
  },
  decisionCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  decisionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  decisionType: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  decisionTypeText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#000',
    textTransform: 'capitalize',
  },
  decisionDate: {
    fontSize: 12,
    color: '#999',
  },
  decisionStatus: {
    fontSize: 12,
    color: '#666',
    textTransform: 'capitalize',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#000',
    marginTop: 16,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
});