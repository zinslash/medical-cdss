import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  SafeAreaView,
  TouchableOpacity
} from 'react-native';

export default function HomePageScreen() {
  return (
    <SafeAreaView style={styles.container}>

      {/* Blue Header Section */}
      <View style={styles.headerBackground}>
        <Text style={styles.welcomeText}>Welcome to the home page!</Text>

        {/* Placeholder Icon (e.g., Notification Bell / Profile) */}
        <TouchableOpacity style={styles.headerIconContainer}>
          <View style={styles.iconPlaceholder} />
        </TouchableOpacity>
      </View>

      {/* Main Body Area */}
      <View style={styles.bodyContent}>
        {/* The rest of your homepage content (buttons, lists, etc.) will go here */}
      </View>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  headerBackground: {
    backgroundColor: '#2260FF',
    height: 155, // Matches the ~152px height from your design
    width: '100%',
    justifyContent: 'center', // Centers the welcome text vertically
    alignItems: 'center',
    position: 'relative',
    paddingHorizontal: 20,
    borderBottomLeftRadius: 15, // Optional: slightly softens the bottom edges
    borderBottomRightRadius: 15,
  },
  welcomeText: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: '600',
    textAlign: 'center',
    textTransform: 'capitalize',
    marginTop: 20, // Pushes text down slightly to account for device status bar
  },
  headerIconContainer: {
    position: 'absolute',
    right: 20,
    bottom: 15, // Places it exactly where the HTML had it (bottom right corner of header)
    padding: 5,
  },
  iconPlaceholder: {
    width: 20,
    height: 22,
    borderWidth: 1.5,
    borderColor: '#FFFFFF',
    borderRadius: 4, // Softens the placeholder square
  },
  bodyContent: {
    flex: 1,
    padding: 24,
    // Ready for your other buttons!
  },
});