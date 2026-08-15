import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  SafeAreaView
} from 'react-native';

export default function PaymentSuccessScreen({ onBackPress }: { onBackPress?: () => void }) {
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBackPress}>
          <Text style={styles.backArrow}>{'<'}</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Payment</Text>
        <View style={styles.headerSpacer} />
      </View>

      {/* Main Content Area */}
      <View style={styles.content}>

        {/* Success Icon Placeholder */}
        <View style={styles.successIconBox}>
          <Text style={styles.checkMark}>✓</Text>
        </View>

        {/* Success Titles */}
        <Text style={styles.titleText}>Congratulations</Text>
        <Text style={styles.subtitleText}>Payment is Successful</Text>

        {/* Appointment Details Card */}
        <View style={styles.detailsCard}>
          <Text style={styles.bookingText}>
            You have successfully booked an appointment with
          </Text>
          <Text style={styles.doctorName}>Dr. Nurul Alam</Text>

          {/* Date and Time Row */}
          <View style={styles.dateTimeContainer}>
            <View style={styles.dateTimeBox}>
              {/* Calendar Icon Placeholder */}
              <View style={styles.iconPlaceholder} />
              <Text style={styles.dateTimeText}>1/1/2020</Text>
            </View>

            <View style={styles.dateTimeBox}>
              {/* Clock Icon Placeholder */}
              <View style={styles.iconPlaceholder} />
              <Text style={styles.dateTimeText}>10:00 AM</Text>
            </View>
          </View>
        </View>

      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2260FF',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 20,
  },
  backButton: {
    padding: 10,
    marginLeft: -10, // Adjust hit area
  },
  backArrow: {
    color: '#FFFFFF',
    fontSize: 28,
    fontWeight: 'bold',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: '600',
  },
  headerSpacer: {
    width: 28, // Matches back button width to keep title perfectly centered
  },
  content: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 40,
  },
  successIconBox: {
    width: 150,
    height: 150,
    borderWidth: 8,
    borderColor: '#FFFFFF',
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 40,
  },
  checkMark: {
    fontSize: 80,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  titleText: {
    color: '#FFFFFF',
    fontSize: 36,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 10,
  },
  subtitleText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '500',
    textAlign: 'center',
    marginBottom: 40,
  },
  detailsCard: {
    width: '100%',
    borderWidth: 1,
    borderColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
  },
  bookingText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '300',
    textAlign: 'center',
    marginBottom: 12,
    lineHeight: 22,
  },
  doctorName: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 24,
  },
  dateTimeContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 30, // Space between date and time
  },
  dateTimeBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconPlaceholder: {
    width: 18,
    height: 18,
    borderWidth: 1,
    borderColor: '#FFFFFF',
    borderRadius: 4,
  },
  dateTimeText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '500',
  },
});