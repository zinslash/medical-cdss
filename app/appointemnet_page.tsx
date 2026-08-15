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

export default function AppointmentSetupScreen({ onBackPress }: { onBackPress?: () => void }) {
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBackPress}>
          <Text style={styles.backArrow}>{'<'}</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Your appointment</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>

        {/* Doctor Card Profile */}
        <View style={styles.doctorCardWrapper}>
          <View style={styles.doctorCardBackground}>
            <View style={styles.doctorDetails}>
              <Text style={styles.doctorName}>Dr. Olivia Turner, M.D.</Text>
              <Text style={styles.doctorSpecialty}>Dermato-Endocrinology</Text>

              {/* Badges / Stats */}
              <View style={styles.badgeContainer}>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>⭐ 5</Text>
                </View>
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>💬 60</Text>
                </View>
              </View>
            </View>

            {/* Action Buttons (Right side of card) */}
            <View style={styles.cardActions}>
              <TouchableOpacity style={styles.iconButton}>
                <Text style={styles.iconText}>♡</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.iconButton}>
                <Text style={styles.iconText}>✉</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Overlapping Doctor Image */}
          <Image
            source={{ uri: 'https://placehold.co/122x122' }}
            style={styles.doctorImage}
          />
        </View>

        <View style={styles.divider} />

        {/* Date and Time Section */}
        <View style={styles.dateTimeSection}>
          <View>
            <View style={styles.datePill}>
              <Text style={styles.dateText}>Month 24, Year</Text>
            </View>
            <Text style={styles.timeText}>WED, 10:00 AM</Text>
          </View>

          <View style={styles.actionButtons}>
            <TouchableOpacity style={styles.squareButton}>
              <Text style={styles.squareButtonIcon}>✓</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.squareButton}>
              <Text style={styles.squareButtonIcon}>✎</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.divider} />

        {/* Patient Details Section */}
        <View style={styles.detailsSection}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Booking for</Text>
            <Text style={styles.detailValue}>Myself</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Full Name</Text>
            <Text style={styles.detailValue}>Zinnatun</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Age</Text>
            <Text style={styles.detailValue}>24</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Gender</Text>
            <Text style={styles.detailValue}>Female</Text>
          </View>
        </View>

        <View style={styles.divider} />

        {/* Problem Description */}
        <View style={styles.problemSection}>
          <Text style={styles.detailLabel}>Problem</Text>
          <Text style={styles.problemDescription}>Lung Problem</Text>
        </View>

      </ScrollView>

      {/* Bottom Navigation / Action Bar Placeholder */}
      <View style={styles.bottomNavContainer}>
        <View style={styles.bottomNavBar}>
          <TouchableOpacity style={styles.navIconPlaceholder} />
          <TouchableOpacity style={styles.navIconPlaceholder} />
          <TouchableOpacity style={styles.navIconPlaceholder} />
        </View>
      </View>
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
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 10,
  },
  backButton: {
    padding: 10,
    marginLeft: -10,
  },
  backArrow: {
    color: '#2260FF',
    fontSize: 28,
    fontWeight: 'bold',
  },
  headerTitle: {
    color: '#2260FF',
    fontSize: 24,
    fontWeight: '600',
  },
  headerSpacer: {
    width: 28,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 100, // Extra space for bottom nav
  },
  doctorCardWrapper: {
    marginTop: 30,
    marginBottom: 20,
    position: 'relative',
    height: 110,
    justifyContent: 'center',
  },
  doctorCardBackground: {
    backgroundColor: '#CAD6FF',
    borderRadius: 17,
    height: 86,
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingLeft: 120, // Make room for the overlapping image
    paddingRight: 15,
    alignItems: 'center',
  },
  doctorImage: {
    width: 100,
    height: 100,
    borderRadius: 20, // Approximate soft edges from HTML
    position: 'absolute',
    left: -10,
    top: 5,
    backgroundColor: '#D9D9D9',
  },
  doctorDetails: {
    flex: 1,
    justifyContent: 'center',
  },
  doctorName: {
    color: '#2260FF',
    fontSize: 14,
    fontWeight: '600',
  },
  doctorSpecialty: {
    color: '#000000',
    fontSize: 12,
    fontWeight: '300',
    marginTop: 2,
  },
  badgeContainer: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
  },
  badge: {
    backgroundColor: '#FFFFFF',
    borderRadius: 13,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  badgeText: {
    color: '#2260FF',
    fontSize: 11,
    fontWeight: '500',
  },
  cardActions: {
    flexDirection: 'column',
    gap: 8,
  },
  iconButton: {
    backgroundColor: '#FFFFFF',
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconText: {
    color: '#2260FF',
    fontSize: 12,
  },
  divider: {
    height: 1,
    backgroundColor: '#2260FF',
    marginVertical: 20,
    opacity: 0.5,
  },
  dateTimeSection: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  datePill: {
    backgroundColor: '#2260FF',
    borderRadius: 18,
    paddingVertical: 6,
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  dateText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '500',
  },
  timeText: {
    color: '#2260FF',
    fontSize: 12,
    fontWeight: '500',
    paddingLeft: 10,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  squareButton: {
    backgroundColor: '#2260FF',
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  squareButtonIcon: {
    color: '#FFFFFF',
    fontSize: 16,
  },
  detailsSection: {
    gap: 15,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  detailLabel: {
    color: '#000000',
    fontSize: 13,
    fontWeight: '300',
  },
  detailValue: {
    color: '#000000',
    fontSize: 13,
    fontWeight: '500',
  },
  problemSection: {
    marginTop: 5,
  },
  problemDescription: {
    color: '#000000',
    fontSize: 13,
    fontWeight: '400',
    marginTop: 8,
    lineHeight: 20,
  },
  bottomNavContainer: {
    position: 'absolute',
    bottom: 30,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  bottomNavBar: {
    backgroundColor: '#2260FF',
    width: '85%',
    height: 55,
    borderRadius: 30,
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    alignItems: 'center',
    shadowColor: '#2260FF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 5,
  },
  navIconPlaceholder: {
    width: 24,
    height: 24,
    borderWidth: 1.5,
    borderColor: '#CAD6FF',
    borderRadius: 6,
  },
});