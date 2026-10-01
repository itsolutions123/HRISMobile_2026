import React, { useContext } from 'react';
import { View, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider, AuthContext } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import TimesheetScreen from './src/screens/TimesheetScreen';
import ManagerScreen from './src/screens/ManagerScreen';
import FormsScreen from './src/screens/FormsScreen';
import HomeScreen from './src/screens/HomeScreen';
import ProfileScreen from './src/screens/ProfileScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabNavigator() {
  const { user } = useContext(AuthContext);

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: '#2563eb' },
        headerTintColor: '#ffffff',
        headerTitleStyle: { fontWeight: 'bold' },
        tabBarActiveTintColor: '#2563eb',
        tabBarInactiveTintColor: '#64748b',
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          if (route.name === 'Home') iconName = focused ? 'home' : 'home-outline';
          else if (route.name === 'Forms') iconName = focused ? 'document-text' : 'document-text-outline';
          else if (route.name === 'Profile') iconName = focused ? 'person' : 'person-outline';
          else if (route.name === 'Admin') iconName = focused ? 'shield-checkmark' : 'shield-checkmark-outline';
          return <Ionicons name={iconName} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ title: 'Home' }} />
      <Tab.Screen name="Forms" component={FormsScreen} options={{ title: 'Forms' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
      {user && ['manager', 'admin', 'superadmin'].includes(String(user.role || '').toLowerCase()) && (
        <Tab.Screen name="Admin" component={ManagerScreen} options={{ title: 'Admin' }} />
      )}
    </Tab.Navigator>
  );
}

const linking = {
  prefixes: ['https://app.bigtimeempire.com', 'http://localhost:19006', 'http://localhost:8087'],
  config: {
    screens: {
      Login: 'login',
      Main: {
        screens: {
          Home: 'admin/home',
          Forms: 'admin/forms',
          Profile: 'admin/profile',
          Admin: 'admin/manager',
        },
      },
    },
  },
};

function NavigationRoot() {
  const { user } = useContext(AuthContext);

  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : (
          <>
            <Stack.Screen name="Main" component={MainTabNavigator} />
            {/* Screens hidden from bottom tabs but accessible via Home screen buttons */}
            <Stack.Screen 
              name="Dashboard" 
              component={DashboardScreen} 
              options={{ headerShown: true, title: 'Time Clock', headerStyle: { backgroundColor: '#2563eb' }, headerTintColor: '#fff' }} 
            />
            <Stack.Screen 
              name="Timesheet" 
              component={TimesheetScreen} 
              options={{ headerShown: true, title: 'Timesheet', headerStyle: { backgroundColor: '#2563eb' }, headerTintColor: '#fff' }} 
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationRoot />
    </AuthProvider>
  );
}
