import React, { useContext } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { AuthProvider, AuthContext } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import TimesheetScreen from './src/screens/TimesheetScreen';
import ManagerScreen from './src/screens/ManagerScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabNavigator() {
  const { user } = useContext(AuthContext);

  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: '#2563eb' },
        headerTintColor: '#ffffff',
        headerTitleStyle: { fontWeight: 'bold' },
        tabBarActiveTintColor: '#2563eb',
        tabBarInactiveTintColor: '#64748b',
      }}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'HRIS Punch' }} />
      <Tab.Screen name="Timesheet" component={TimesheetScreen} options={{ title: 'Timesheet' }} />
      {user && user.role === 'manager' && (
        <Tab.Screen name="Manager" component={ManagerScreen} options={{ title: 'Oversight' }} />
      )}
    </Tab.Navigator>
  );
}

function NavigationRoot() {
  const { user } = useContext(AuthContext);

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} />
        ) : (
          <Stack.Screen name="Main" component={MainTabNavigator} />
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
