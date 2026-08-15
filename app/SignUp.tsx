import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert, SafeAreaView, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';

export default function SignUpScreen({ navigation }: any) {
  // 2. Add inside your component, right above your state variables
  const router = useRouter();

  // ... (your existing state and handleSignUp code) ...

  return (
    // ... (your existing UI code) ...

    {/* 3. Add this right BELOW your "Register Profile" TouchableOpacity */}
    <TouchableOpacity onPress={() => router.push('/login')} style={{ marginTop: 20, alignItems: 'center' }}>
      <Text style={{ color: '#2260FF', fontSize: 14 }}>Already have an account? Log in here</Text>
    </TouchableOpacity>
  );
}

export default function SignUpScreen({ navigation }: any) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [problem, setProblem] = useState('');

  const handleSignUp = async () => {
    try {
      // ⚠️ Note: For Android Emulator use 'http://10.0.2.2:8000/api/signup_patient'
      // For iOS Simulator or web use 'http://127.0.0.1:8000/api/signup_patient'
      const response = await fetch('http://127.0.0.1:8000/api/signup_patient', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fullName: fullName,
          email: email,
          password: password,
          age: age ? parseInt(age, 10) : null,
          gender: gender,
          problem: problem,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        Alert.alert("Success", data.message || "Patient profile created successfully!");
        // TODO: Navigate to login or home screen here
      } else {
        Alert.alert("Error", data.message || "Email already exists or invalid data.");
      }
    } catch (error) {
      console.error("Network error:", error);
      Alert.alert("Connection Error", "Could not connect to the backend server.");
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Patient Sign Up</Text>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Full Name</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your full name"
            placeholderTextColor="#A9BCFE"
            value={fullName}
            onChangeText={setFullName}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your email"
            placeholderTextColor="#A9BCFE"
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your password"
            placeholderTextColor="#A9BCFE"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Age</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your age"
            placeholderTextColor="#A9BCFE"
            keyboardType="numeric"
            value={age}
            onChangeText={setAge}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Gender</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your gender"
            placeholderTextColor="#A9BCFE"
            value={gender}
            onChangeText={setGender}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.label}>Problem</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., Lung Problem"
            placeholderTextColor="#A9BCFE"
            value={problem}
            onChangeText={setProblem}
          />
        </View>

        <TouchableOpacity style={styles.button} onPress={handleSignUp}>
          <Text style={styles.buttonText}>Register Profile</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF'
  },
  scrollContent: {
    padding: 24,
    justifyContent: 'center'
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#2260FF',
    marginBottom: 24,
    textAlign: 'center',
    fontFamily: 'League Spartan'
  },
  inputContainer: {
    marginBottom: 15,
  },
  label: {
    fontSize: 13,
    fontWeight: '300',
    color: '#000000',
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: '#CAD6FF',
    padding: 12,
    borderRadius: 13,
    fontSize: 14,
    color: '#000000',
    backgroundColor: '#FFFFFF'
  },
  button: {
    backgroundColor: '#2260FF',
    padding: 16,
    borderRadius: 20,
    alignItems: 'center',
    marginTop: 15,
    shadowColor: '#2260FF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 3
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600'
  }
});