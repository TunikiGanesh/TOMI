import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  FlatList,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const DOCUMENT_CATEGORIES = [
  { id: 'supplier', name: 'Supplier Lists', icon: 'people', description: 'Vendor and supplier information' },
  { id: 'customer', name: 'Customer Data', icon: 'person', description: 'Customer databases and contacts' },
  { id: 'financial', name: 'Financial Docs', icon: 'cash', description: 'Statements, invoices, receipts' },
  { id: 'pricing', name: 'Pricing Sheets', icon: 'pricetag', description: 'Price lists and quotes' },
  { id: 'policy', name: 'Policies', icon: 'document-text', description: 'Contracts, terms, policies' },
  { id: 'faq', name: 'FAQs', icon: 'help-circle', description: 'Frequently asked questions' },
  { id: 'forms', name: 'Forms', icon: 'clipboard', description: 'Intake forms, templates' },
  { id: 'other', name: 'Other', icon: 'folder', description: 'Other business documents' },
];

interface Document {
  id: string;
  name: string;
  category: string;
  size: number;
  uploading: boolean;
  error?: string;
}

export default function KnowledgeImport() {
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [completing, setCompleting] = useState(false);

  const pickDocument = async (category: string) => {
    try {
      console.log('Picking document for category:', category);
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          'application/pdf',
          'application/vnd.ms-excel',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'text/csv',
          'text/plain',
          'image/*',
        ],
        copyToCacheDirectory: true,
      });

      console.log('Document picker result:', result);

      if (result.canceled) {
        console.log('Document picker canceled');
        return;
      }

      const file = result.assets[0];
      console.log('Selected file:', file);
      await uploadDocument(file, category);
    } catch (error) {
      console.error('Document picker error:', error);
      Alert.alert('Error', `Failed to pick document: ${error.message || 'Unknown error'}`);
    }
  };

  const pickImage = async (category: string) => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Please allow access to your photo library');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsMultipleSelection: false,
      });

      if (result.canceled) return;

      const asset = result.assets[0];
      await uploadDocument({
        uri: asset.uri,
        name: asset.fileName || `image_${Date.now()}.jpg`,
        type: 'image/jpeg',
        size: asset.fileSize,
      }, category);
    } catch (error) {
      console.error('Image picker error:', error);
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const uploadDocument = async (file: any, category: string) => {
    const tempId = `temp_${Date.now()}`;
    const newDoc: Document = {
      id: tempId,
      name: file.name,
      category,
      size: file.size || 0,
      uploading: true,
    };

    setDocuments(prev => [...prev, newDoc]);

    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        type: file.type || file.mimeType || 'application/octet-stream',
        name: file.name,
      } as any);
      formData.append('category', category);

      const response = await fetch(`${API_URL}/api/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setDocuments(prev =>
          prev.map(doc =>
            doc.id === tempId
              ? { ...doc, id: data.document_id, uploading: false }
              : doc
          )
        );

        Alert.alert('Success', `Extracted ${data.extracted_text.length} characters from ${file.name}`);
      } else {
        const error = await response.json();
        setDocuments(prev =>
          prev.map(doc =>
            doc.id === tempId
              ? { ...doc, uploading: false, error: error.detail }
              : doc
          )
        );
        Alert.alert('Upload Failed', error.detail || 'Could not process document');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setDocuments(prev =>
        prev.map(doc =>
          doc.id === tempId
            ? { ...doc, uploading: false, error: 'Network error' }
            : doc
        )
      );
      Alert.alert('Error', 'Failed to upload document');
    }
  };

  const removeDocument = async (docId: string) => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      const response = await fetch(`${API_URL}/api/documents/${docId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setDocuments(prev => prev.filter(doc => doc.id !== docId));
      } else {
        Alert.alert('Error', 'Failed to delete document');
      }
    } catch (error) {
      console.error('Delete error:', error);
      Alert.alert('Error', 'Failed to delete document');
    }
  };

  const completeOnboarding = async () => {
    setCompleting(true);
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      const response = await fetch(`${API_URL}/api/onboarding/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        
        // Update stored user
        const userStr = await AsyncStorage.getItem('user');
        if (userStr) {
          const user = JSON.parse(userStr);
          user.onboarding_completed = true;
          await AsyncStorage.setItem('user', JSON.stringify(user));
        }

        const message = data.has_knowledge_base
          ? `Great! TOMI has processed ${data.documents_uploaded} documents and is ready to assist you.`
          : 'TOMI will learn from your future interactions and get smarter over time.';

        Alert.alert(
          'Welcome to TOMI!',
          message,
          [{ text: 'Get Started', onPress: () => router.replace('/(tabs)/home') }]
        );
      } else {
        const error = await response.json();
        Alert.alert('Error', error.detail || 'Could not complete onboarding');
      }
    } catch (error) {
      console.error('Onboarding completion error:', error);
      Alert.alert('Error', 'Failed to complete setup');
    } finally {
      setCompleting(false);
    }
  };

  const skipForNow = () => {
    Alert.alert(
      'Continue Without Documents?',
      'You can always upload documents later to improve TOMI\'s suggestions.\n\nWithout documents, TOMI will learn from your future interactions and decisions.',
      [
        { text: 'Upload Now', style: 'cancel' },
        { text: 'Continue', onPress: completeOnboarding },
      ]
    );
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
              <View style={[styles.progressFill, { width: '100%' }]} />
            </View>
            <Text style={styles.progressText}>Step 3 of 3</Text>
          </View>
          
          <Text style={styles.title}>Import Your Knowledge (Optional)</Text>
          <Text style={styles.subtitle}>
            Upload business documents to give TOMI context and improve AI suggestions. You can skip this and TOMI will learn from your future interactions.
          </Text>
        </View>

        <View style={styles.categorySection}>
          <Text style={styles.sectionTitle}>What documents do you have?</Text>
          
          <View style={styles.categoryGrid}>
            {DOCUMENT_CATEGORIES.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={styles.categoryCard}
                onPress={() =>
                  Alert.alert(
                    `Upload ${category.name}`,
                    'Choose upload method',
                    [
                      { text: 'Choose File', onPress: () => pickDocument(category.id) },
                      { text: 'Take Photo', onPress: () => pickImage(category.id) },
                      { text: 'Cancel', style: 'cancel' },
                    ]
                  )
                }
              >
                <Ionicons name={category.icon as any} size={32} color="#007AFF" />
                <Text style={styles.categoryName}>{category.name}</Text>
                <Text style={styles.categoryDescription}>{category.description}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {documents.length > 0 && (
          <View style={styles.uploadedSection}>
            <Text style={styles.sectionTitle}>
              Uploaded Documents ({documents.filter(d => !d.uploading).length})
            </Text>
            
            {documents.map((doc) => (
              <View key={doc.id} style={styles.documentItem}>
                <View style={styles.documentLeft}>
                  {doc.uploading ? (
                    <ActivityIndicator size="small" color="#007AFF" />
                  ) : doc.error ? (
                    <Ionicons name="alert-circle" size={24} color="#FF3B30" />
                  ) : (
                    <Ionicons name="checkmark-circle" size={24} color="#34C759" />
                  )}
                  <View style={styles.documentInfo}>
                    <Text style={styles.documentName}>{doc.name}</Text>
                    <Text style={styles.documentMeta}>
                      {doc.category} • {(doc.size / 1024).toFixed(1)} KB
                    </Text>
                    {doc.error && (
                      <Text style={styles.documentError}>{doc.error}</Text>
                    )}
                  </View>
                </View>
                
                {!doc.uploading && (
                  <TouchableOpacity
                    onPress={() => removeDocument(doc.id)}
                    style={styles.deleteButton}
                  >
                    <Ionicons name="trash-outline" size={20} color="#FF3B30" />
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </View>
        )}

        <View style={styles.infoBox}>
          <Ionicons name="shield-checkmark" size={20} color="#34C759" />
          <Text style={styles.infoText}>
            Your documents are encrypted and private. TOMI uses them only to understand your business context.
          </Text>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.skipButton}
          onPress={skipForNow}
        >
          <Text style={styles.skipButtonText}>Skip for Now</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, completing && styles.buttonDisabled]}
          onPress={completeOnboarding}
          disabled={completing}
        >
          {completing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Text style={styles.buttonText}>Complete Setup</Text>
              <Ionicons name="checkmark" size={20} color="#fff" />
            </>
          )}
        </TouchableOpacity>
      </View>
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
    paddingBottom: 100,
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
    lineHeight: 24,
  },
  categorySection: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    marginBottom: 16,
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  categoryCard: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E5E5',
    backgroundColor: '#F9F9F9',
    alignItems: 'center',
    minHeight: 120,
  },
  categoryName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginTop: 8,
    textAlign: 'center',
  },
  categoryDescription: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textAlign: 'center',
  },
  uploadedSection: {
    marginBottom: 24,
  },
  documentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F9F9F9',
    marginBottom: 8,
  },
  documentLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: 12,
  },
  documentInfo: {
    flex: 1,
  },
  documentName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#000',
  },
  documentMeta: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  documentError: {
    fontSize: 12,
    color: '#FF3B30',
    marginTop: 2,
  },
  deleteButton: {
    padding: 8,
  },
  infoBox: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#F0FFF4',
    borderRadius: 8,
    gap: 8,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 24,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#E5E5E5',
    flexDirection: 'row',
    gap: 12,
  },
  skipButton: {
    flex: 1,
    height: 50,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#007AFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  button: {
    flex: 1,
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
