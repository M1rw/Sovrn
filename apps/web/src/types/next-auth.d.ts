import { DefaultSession, DefaultUser } from 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      email: string;
      name?: string | null;
    } & DefaultSession['user'];
    accessToken: string;
    refreshToken?: string;
  }

  interface User extends DefaultUser {
    id: string;
    email: string;
    name?: string | null;
    accessToken: string;
    refreshToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id?: string;
    email?: string;
    name?: string | null;
    accessToken?: string;
    refreshToken?: string;
  }
}
