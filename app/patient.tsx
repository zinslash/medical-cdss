import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  TouchableOpacity,
  SafeAreaView,
  ScrollView
} from 'react-native';

export default function PatientProfileScreen({ onBackPress }: { onBackPress?: () => void }) {
  return (
    <SafeAreaView style={styles.container}>
      {/* Header (Matching your Doctor Profile style) */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBackPress}>
          <Text style={styles.backArrow}>{'<'}</Text>
        </TouchableOpacity>

        {/* Segmented Controls */}
        <View style={styles.headerControls}>
          <TouchableOpacity style={styles.activeControl}>
            <Text style={styles.activeControlText}>Schedule</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.inactiveControl}>
            <Text style={styles.iconText}>🎥</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.inactiveControl}>
            <Text style={styles.iconText}>💬</Text>
          </TouchableOpacity>
        </View>

        {/* Right Actions */}
        <View style={styles.headerActions}>
          <TouchableOpacity style={styles.inactiveControl}>
            <Text style={styles.iconText}>?</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.inactiveControl}>
            <Text style={styles.iconText}>♡</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>

        {/* Main Blue Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.avatarContainer}>
            <Image
              source={{ uri: 'https://placehold.co/122x122' }}
              style={styles.avatarImage}
            />
          </View>

          <View style={styles.nameBadge}>
            <Text style={styles.patientName}>Patient Name</Text>
            <Text style={styles.patientId}>Patient ID</Text>
          </View>
        </View>

        {/* Timeline Section */}
        <View style={styles.timelineSection}>
          <Text style={styles.timelineTitle}>Your result timeline:</Text>

          {/* Timeline Result Card */}
          <View style={styles.resultCard}>
            <View style={styles.resultRow}>
              <Text style={styles.resultLabel}>X-Ray:</Text>
              <Text style={styles.resultValue}>Lung</Text>
            </View>
            <View style={styles.resultRow}>
              <Text style={styles.resultLabel}>Detection:</Text>
              <Text style={styles.resultValue}>Pneumonia</Text>
            </View>
            <View style={styles.resultRow}>
              <Text style={styles.resultLabel}>AI Confidence:</Text>
              <Text style={styles.resultValue}>97.3 %</Text>
            </View>
            <View style={styles.resultRow}>
              <Text style={styles.resultLabel}>Date:</Text>
              <Text style={styles.resultValue}>3/01/2025</Text>
            </View>
          </View>

          {/* Add more <View style={styles.resultCard}> here when fetching from database */}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 15,
    paddingBottom: 10,
  },
  backButton: {
    padding: 5,
  },
  backArrow: {
    color: '#2260FF',
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerControls: {
    flexDirection: 'row',
    gap: 8,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  activeControl: {
    backgroundColor: '#2260FF',
    borderRadius: 15,
    paddingVertical: 6,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  activeControlText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '500',
  },
  inactiveControl: {
    backgroundColor: '#CAD6FF',
    borderRadius: 15,
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconText: {
    color: '#2260FF',
    fontSize: 14,
    fontWeight: 'bold',
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 40,
  },
  profileCard: {
    backgroundColor: '#CAD6FF',
    borderRadius: 17,
    paddingVertical: 30,
    alignItems: 'center',
    marginBottom: 30,
  },
  avatarContainer: {
    width: 122,
    height: 122,
    borderRadius: 61,
    backgroundColor: '#D9D9D9',
    overflow: 'hidden',
    marginBottom: 20,
  },
  avatarImage: {
    width: '100%',
    height: '100%',
  },
  nameBadge: {
    backgroundColor: '#FFFFFF',
    borderRadius: 13,
    paddingVertical: 8,
    paddingHorizontal: 24,
    alignItems: 'center',
    width: '80%',
  },
  patientName: {
    color: '#2260FF',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  patientId: {
    color: '#000000',
    fontSize: 12,
    fontWeight: '300',
  },
  timelineSection: {
    marginTop: 10,
  },
  timelineTitle: {
    color: '#0088FF',
    fontSize: 22,
    fontWeight: '500',
    marginBottom: 15,
    textTransform: 'capitalize',
  },
  resultCard: {
    backgroundColor: '#F0F0F0', // Slightly lighter than pure #D9D9D9 for better text contrast
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  resultRow: {
    flexDirection: 'row',
    marginBottom: 6,
  },
  resultLabel: {
    color: '#000000',
    fontSize: 15,
    fontWeight: '600',
    width: 120, // Keeps the columns aligned
  },
  resultValue: {
    color: '#333333',
    fontSize: 15,
    fontWeight: '400',
    flex: 1,
  },
});