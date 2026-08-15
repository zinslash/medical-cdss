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

export default function DoctorProfileScreen({ onBackPress }: { onBackPress?: () => void }) {
  // Calendar data helpers for rendering
  const daysOfWeek = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
  // Simplified array for visual structure (1 to 31)
  const calendarDates = Array.from({ length: 31 }, (_, i) => i + 1);

  return (
    <SafeAreaView style={styles.container}>
      {/* Custom Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBackPress}>
          <Text style={styles.backArrow}>{'<'}</Text>
        </TouchableOpacity>

        {/* Segmented Controls Placeholder */}
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
          <View style={styles.cardTopRow}>
            {/* Left Side: Avatar & Name */}
            <View style={styles.avatarSection}>
              <View style={styles.avatarContainer}>
                <Image
                  source={{ uri: 'https://placehold.co/122x122' }}
                  style={styles.avatarImage}
                />
              </View>
              <View style={styles.nameContainer}>
                <Text style={styles.doctorName}>Dr. Nurul Alam</Text>
                <Text style={styles.doctorSpecialty}>Orthopedic Surgeon</Text>
              </View>
            </View>

            {/* Right Side: Experience & Focus */}
            <View style={styles.statsSection}>
              <View style={styles.experienceBadge}>
                <View style={styles.experienceIconPlaceholder} />
                <View>
                  <Text style={styles.experienceText}>20 years</Text>
                  <Text style={styles.experienceSubText}>experience</Text>
                </View>
              </View>

              <View style={styles.focusBox}>
                <Text style={styles.focusTitle}>Focus:</Text>
                <Text style={styles.focusItem}>Lung disease</Text>
                <Text style={styles.focusItem}>• Lung problems</Text>
                <Text style={styles.focusItem}>• Lung specialist</Text>
              </View>
            </View>
          </View>

          {/* Bottom Card Badges */}
          <View style={styles.cardBottomRow}>
            <View style={styles.infoBadge}>
              <Text style={styles.infoBadgeText}>⭐ 5</Text>
            </View>
            <View style={styles.infoBadge}>
              <Text style={styles.infoBadgeText}>⏰ Mon - Sat / 9 AM - 4 PM</Text>
            </View>
          </View>
        </View>

        {/* Biography Section */}
        <View style={styles.bioSection}>
          <Text style={styles.sectionTitle}>Profile</Text>
          <Text style={styles.bioText}>
            Hi, I'm Dr. Alam, I'm looking forward to working with you to reach your health goals today.
          </Text>
          <Text style={[styles.sectionTitle, { marginTop: 15 }]}>Scheduling Time:</Text>
        </View>

      </ScrollView>

      {/* Fixed Calendar Section at the Bottom */}
      <View style={styles.calendarContainer}>
        {/* Month Selector */}
        <View style={styles.monthSelector}>
          <Text style={styles.monthArrow}>{'<'}</Text>
          <Text style={styles.monthText}>MONTH</Text>
          <Text style={styles.monthArrow}>{'>'}</Text>
        </View>

        {/* Calendar Inner White Box */}
        <View style={styles.calendarBox}>
          {/* Days of Week */}
          <View style={styles.daysRow}>
            {daysOfWeek.map((day, index) => (
              <View key={index} style={styles.dayPill}>
                <Text style={styles.dayText}>{day}</Text>
              </View>
            ))}
          </View>

          {/* Dates Grid */}
          <View style={styles.datesGrid}>
            {calendarDates.map((date) => {
              const isSelected = date === 24; // Highlighting the 24th as per the design
              return (
                <View key={date} style={styles.dateCell}>
                  <View style={[styles.dateCircle, isSelected && styles.selectedDateCircle]}>
                    <Text style={[styles.dateText, isSelected && styles.selectedDateText]}>
                      {date}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
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
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  profileCard: {
    backgroundColor: '#CAD6FF',
    borderRadius: 20,
    padding: 16,
    marginBottom: 20,
  },
  cardTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  avatarSection: {
    flex: 1,
    alignItems: 'center',
    marginRight: 10,
  },
  avatarContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#D9D9D9',
    overflow: 'hidden',
    marginBottom: 10,
  },
  avatarImage: {
    width: '100%',
    height: '100%',
  },
  nameContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
    width: '100%',
    alignItems: 'center',
  },
  doctorName: {
    color: '#2260FF',
    fontSize: 13,
    fontWeight: '600',
  },
  doctorSpecialty: {
    color: '#000000',
    fontSize: 10,
    fontWeight: '300',
    marginTop: 2,
  },
  statsSection: {
    flex: 1,
    gap: 10,
  },
  experienceBadge: {
    backgroundColor: '#2260FF',
    borderRadius: 15,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 10,
    gap: 8,
  },
  experienceIconPlaceholder: {
    width: 16,
    height: 16,
    backgroundColor: '#CAD6FF',
    borderRadius: 8,
  },
  experienceText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '500',
  },
  experienceSubText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: '300',
  },
  focusBox: {
    backgroundColor: '#2260FF',
    borderRadius: 15,
    padding: 12,
    flex: 1,
  },
  focusTitle: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
  },
  focusItem: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '300',
    marginBottom: 2,
  },
  cardBottomRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
  },
  infoBadge: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  infoBadgeText: {
    color: '#2260FF',
    fontSize: 11,
    fontWeight: '500',
  },
  bioSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    color: '#2260FF',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  bioText: {
    color: '#000000',
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 20,
  },
  calendarContainer: {
    backgroundColor: '#CAD6FF',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: 20,
    paddingBottom: 40,
  },
  monthSelector: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 15,
    marginBottom: 15,
  },
  monthText: {
    color: '#2260FF',
    fontSize: 14,
    fontWeight: '600',
  },
  monthArrow: {
    color: '#2260FF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  calendarBox: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 15,
  },
  daysRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  dayPill: {
    backgroundColor: '#2260FF',
    borderRadius: 12,
    paddingVertical: 4,
    width: 32,
    alignItems: 'center',
  },
  dayText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '500',
    textTransform: 'uppercase',
  },
  datesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  dateCell: {
    width: '14.28%', // 7 days in a row
    aspectRatio: 1, // Keep cells square
    justifyContent: 'center',
    alignItems: 'center',
  },
  dateCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  selectedDateCircle: {
    backgroundColor: '#2260FF',
  },
  dateText: {
    color: '#A9BCFE', // Light blue for unselected
    fontSize: 12,
    fontWeight: '400',
  },
  selectedDateText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
});