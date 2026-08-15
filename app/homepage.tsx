import React, { useState } from "react";
import { StyleSheet, Text, View, TextInput, TouchableOpacity, SafeAreaView, KeyboardAvoidingView, Platform, ScrollView, Dimensions } from "react-native";

const { width } = Dimensions.get('window');

// 1. First Screen: Welcome / Landing
export function FirstScreen({ onNavigateToLogin, onNavigateToSignUp }: { onNavigateToLogin?: () => void; onNavigateToSignUp?: () => void }) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.logoContainer}>
          <Text style={styles.title}>AI TRIAGE</Text>
          <Text style={styles.subtitle}>MEDICAL ASSISTANT</Text>
        </View>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.primaryButton} onPress={onNavigateToLogin} activeOpacity={0.8}>
            <Text style={styles.primaryButtonText}>Log In</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.outlineButton} onPress={onNavigateToSignUp} activeOpacity={0.8}>
            <Text style={styles.outlineButtonText}>Sign Up</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

// 2. Login Screen ("Log In 2")
export function LoginScreen({ onNavigateToSignUp, onLoginSuccess }: { onNavigateToSignUp?: () => void; onLoginSuccess?: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.inner}>
        <View style={styles.headerContainer}>
          <Text style={styles.heading}>Hello!</Text>
          <Text style={styles.subheading}>Welcome, To The Sign In Page!</Text>
        </View>
        <View style={styles.formContainer}>
          <Text style={styles.label}>Email or Mobile Number</Text>
          <TextInput style={styles.input} placeholder="Enter email or mobile number" value={email} onChangeText={setEmail} autoCapitalize="none" placeholderTextColor="#9CA3AF" />
          <Text style={styles.label}>Password</Text>
          <View style={styles.passwordContainer}>
            <TextInput style={styles.passwordInput} placeholder="Enter password" value={password} onChangeText={setPassword} secureTextEntry={!passwordVisible} placeholderTextColor="#9CA3AF" />
            <TouchableOpacity onPress={() => setPasswordVisible(!passwordVisible)} style={styles.eyeButton}>
              <Text style={styles.eyeText}>{passwordVisible ? 'Hide' : 'Show'}</Text>
            </TouchableOpacity>
          </View>
        </View>
        <TouchableOpacity style={styles.primaryButton} onPress={onLoginSuccess}>
          <Text style={styles.primaryButtonText}>Log In</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.linkContainer} onPress={onNavigateToSignUp}>
          <Text style={styles.linkText}>Don't have an account? <Text style={styles.linkBold}>Sign Up</Text></Text>
        </TouchableOpacity>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// 3. Sign Up Screen
export function SignUpScreen({ onNavigateBack, onNavigateToLogin, onSignUpSuccess }: { onNavigateBack?: () => void; onNavigateToLogin?: () => void; onSignUpSuccess?: () => void }) {
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [mobileNumber, setMobileNumber] = useState('');
  const [dob, setDob] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <View style={styles.backHeader}>
            <TouchableOpacity onPress={onNavigateBack} style={{ paddingRight: 15 }}>
              <Text style={styles.backArrow}>{'<'}</Text>
            </TouchableOpacity>
            <Text style={styles.headingSmall}>Sign Up Account</Text>
          </View>
          <Text style={styles.label}>Full name</Text>
          <TextInput style={styles.input} placeholder="Enter full name" value={fullName} onChangeText={setFullName} placeholderTextColor="#9CA3AF" />
          <Text style={styles.label}>Password</Text>
          <View style={styles.passwordContainer}>
            <TextInput style={styles.passwordInput} placeholder="Enter password" value={password} onChangeText={setPassword} secureTextEntry={!passwordVisible} placeholderTextColor="#9CA3AF" />
            <TouchableOpacity onPress={() => setPasswordVisible(!passwordVisible)} style={styles.eyeButton}>
              <Text style={styles.eyeText}>{passwordVisible ? 'Hide' : 'Show'}</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.label}>Email</Text>
          <TextInput style={styles.input} placeholder="Enter email" value={email} onChangeText={setEmail} autoCapitalize="none" placeholderTextColor="#9CA3AF" />
          <Text style={styles.label}>Mobile Number</Text>
          <TextInput style={styles.input} placeholder="Enter mobile number" value={mobileNumber} onChangeText={setMobileNumber} keyboardType="phone-pad" placeholderTextColor="#9CA3AF" />
          <Text style={styles.label}>Date Of Birth</Text>
          <TextInput style={styles.input} placeholder="DD/MM/YYYY" value={dob} onChangeText={setDob} placeholderTextColor="#9CA3AF" />
          <TouchableOpacity style={[styles.primaryButton, { marginTop: 20 }]} onPress={onSignUpSuccess}>
            <Text style={styles.primaryButtonText}>Sign Up</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkContainer} onPress={onNavigateToLogin}>
            <Text style={styles.linkText}>Already have an account? <Text style={styles.linkBold}>Log In</Text></Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// 4. Home / Dashboard Screen
export function HomeScreen({ onAmbulancePress, onAppointmentPress, onUploadPress }: { onAmbulancePress?: () => void; onAppointmentPress?: () => void; onUploadPress?: () => void }) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.homeHeader}>
        <Text style={styles.homeTitle}>Welcome To The Home Page!</Text>
        <Text style={styles.homeSubtitle}>Upload Your X-Ray To Receive Results!</Text>
      </View>
      <View style={styles.homeBody}>
        <TouchableOpacity style={styles.uploadBoxButton} onPress={onUploadPress}>
          <Text style={styles.uploadText}>Upload</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButtonAmbulance} onPress={onAmbulancePress}>
          <Text style={styles.actionButtonText}>Immediately Pay For The Ambulance</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButtonAppointment} onPress={onAppointmentPress}>
          <Text style={styles.actionButtonText}>Book An Appointment for Doctor</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  content: { flex: 1, justifyContent: 'space-between', alignItems: 'center', paddingVertical: 60, paddingHorizontal: 30, backgroundColor: '#1E60FF' },
  logoContainer: { alignItems: 'center', marginTop: 100 },
  title: { fontSize: 34, fontWeight: 'bold', color: '#FFFFFF', letterSpacing: 2, textAlign: 'center' },
  subtitle: { fontSize: 12, color: '#D1E0FF', letterSpacing: 3, marginTop: 8, fontWeight: '600', textAlign: 'center' },
  buttonContainer: { width: '100%', marginBottom: 20 },
  primaryButton: { backgroundColor: '#1E60FF', borderRadius: 28, paddingVertical: 16, alignItems: 'center', shadowColor: '#1E60FF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.25, shadowRadius: 8, elevation: 4 },
  primaryButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  outlineButton: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: '#FFFFFF', paddingVertical: 16, borderRadius: 30, alignItems: 'center' },
  outlineButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  inner: { flex: 1, paddingHorizontal: 28, justifyContent: 'center' },
  headerContainer: { marginBottom: 32 },
  heading: { fontSize: 32, fontWeight: 'bold', color: '#1E60FF', marginBottom: 6 },
  headingSmall: { fontSize: 22, fontWeight: 'bold', color: '#1E60FF' },
  subheading: { fontSize: 16, color: '#6B7280' },
  formContainer: { marginBottom: 20 },
  label: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 8 },
  input: { backgroundColor: '#F3F4F6', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: '#1F2937', borderWidth: 1, borderColor: '#E5E7EB', marginBottom: 16 },
  passwordContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F3F4F6', borderRadius: 12, borderWidth: 1, borderColor: '#E5E7EB', paddingHorizontal: 16, marginBottom: 16 },
  passwordInput: { flex: 1, paddingVertical: 14, fontSize: 15, color: '#1F2937' },
  eyeButton: { paddingLeft: 10 },
  eyeText: { color: '#1E60FF', fontSize: 14, fontWeight: '600' },
  linkContainer: { marginTop: 20, alignItems: 'center' },
  linkText: { fontSize: 14, color: '#6B7280' },
  linkBold: { color: '#1E60FF', fontWeight: 'bold' },
  scrollContent: { flexGrow: 1, paddingHorizontal: 28, paddingVertical: 20 },
  backHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 30, marginTop: 10 },
  backArrow: { fontSize: 24, color: '#1E60FF', fontWeight: 'bold' },
  homeHeader: { width: '100%', height: 156, backgroundColor: '#225FFF', justifyContent: 'center', alignItems: 'center', paddingTop: 20 },
  homeTitle: { fontSize: 20, fontWeight: '600', color: '#FFFFFF', textAlign: 'center' },
  homeSubtitle: { fontSize: 14, fontWeight: '600', color: '#FFFFFF', textAlign: 'center', marginTop: 8 },
  homeBody: { flex: 1, alignItems: 'center', justifyContent: 'center', position: 'relative' },
  uploadBoxButton: { backgroundColor: '#D9D9D9', width: 80, height: 30, justifyContent: 'center', alignItems: 'center', marginBottom: 30 },
  uploadText: { fontSize: 16, fontWeight: '600', color: '#000000' },
  actionButtonAmbulance: { backgroundColor: '#D9D9D9', width: 180, height: 35, justifyContent: 'center', alignItems: 'center', marginBottom: 15, paddingHorizontal: 5 },
  actionButtonAppointment: { backgroundColor: '#D9D9D9', width: 180, height: 35, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 5 },
  actionButtonText: { fontSize: 12, fontWeight: '500', color: '#000000', textAlign: 'center' }
});