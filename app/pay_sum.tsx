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

export default function PaymentSummaryScreen({ onBackPress, onPayPress, onChangeMethod }: any) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>

        {/* Header Area */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={onBackPress}>
            <Text style={styles.backArrow}>{'<'}</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Payment</Text>
          <Text style={styles.headerAmount}>TK 1000.00</Text>
        </View>

        {/* Main Content Card (Overlaps the header slightly) */}
        <View style={styles.contentCard}>

          {/* Doctor Profile Header */}
          <View style={styles.doctorInfoContainer}>
            {/* Fake Heart Icon */}
            <TouchableOpacity style={styles.favoriteButton}>
              <Text style={styles.favoriteIcon}>♡</Text>
            </TouchableOpacity>

            <Image
              source={{ uri: 'https://api.builder.io/api/v1/image/assets/TEMP/3ae6e44e0283f1a93ed85038dc27860a9f3840e2?width=118' }}
              style={styles.avatar}
            />

            <View style={styles.doctorTextContainer}>
              <Text style={styles.doctorName}>Dr. Nurul Alam</Text>
              <Text style={styles.doctorSpecialty}>Orthopedic Surgeon</Text>

              <View style={styles.badgeRow}>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>⭐ 5</Text>
                </View>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>💬 60</Text>
                </View>
              </View>
            </View>
          </View>

          {/* Details Section */}
          <View style={styles.detailsSection}>
            <View style={styles.divider} />

            <View style={styles.row}>
              <Text style={styles.rowLabel}>Date / Hour</Text>
              <Text style={styles.rowValue}>Month 24, Year / 10:00 AM</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Duration</Text>
              <Text style={styles.rowValue}>30 minutes</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Booking for</Text>
              <Text style={styles.rowValue}>another person</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <Text style={styles.rowLabel}>Amount</Text>
              <Text style={styles.rowValue}>$100.00</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Duration</Text>
              <Text style={styles.rowValue}>30 minutes</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Total</Text>
              <Text style={styles.rowValue}>$100</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.row}>
              <Text style={styles.rowLabel}>Payment Method</Text>
              <View style={styles.methodContainer}>
                <Text style={styles.rowValue}>Card</Text>
                <TouchableOpacity onPress={onChangeMethod}>
                  <Text style={styles.changeText}>Change</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Pay Button */}
          <TouchableOpacity style={styles.payButton} onPress={onPayPress}>
            <Text style={styles.payButtonText}>Pay now</Text>
          </TouchableOpacity>

        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#EAF0FF', // Light brand background
  },
  header: {
    backgroundColor: '#2260FF',
    paddingTop: 40,
    paddingBottom: 60,
    alignItems: 'center',
    position: 'relative',
  },
  backButton: {
    position: 'absolute',
    left: 20,
    top: 45,
    padding: 5,
  },
  backArrow: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '600',
  },
  headerAmount: {
    color: '#FFFFFF',
    fontSize: 34,
    fontWeight: 'bold',
    marginTop: 20,
  },
  contentCard: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    marginTop: -30, // Pulls the card up over the blue header
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 40,
  },
  doctorInfoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
    position: 'relative',
  },
  favoriteButton: {
    position: 'absolute',
    top: 0,
    right: 0,
    backgroundColor: '#2260FF',
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  favoriteIcon: {
    color: '#FFFFFF',
    fontSize: 14,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#D9D9D9',
    marginRight: 16,
  },
  doctorTextContainer: {
    flex: 1,
  },
  doctorName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  doctorSpecialty: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  badgeRow: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
  },
  badge: {
    backgroundColor: '#EAF0FF',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 12,
    color: '#2260FF',
    fontWeight: '500',
  },
  detailsSection: {
    marginBottom: 30,
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 16,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  rowLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  rowValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1F2937',
  },
  methodContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  changeText: {
    fontSize: 14,
    color: '#2260FF',
    textDecorationLine: 'underline',
  },
  payButton: {
    backgroundColor: '#2260FF',
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#2260FF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  payButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
