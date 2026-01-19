import { PrismaClient, Plan } from '@prisma/client';
import * as crypto from 'crypto';

const prisma = new PrismaClient();

/**
 * Simple password hashing for seed data.
 * In production, use bcrypt or argon2 from the API.
 */
function hashPassword(password: string): string {
  return crypto.createHash('sha256').update(password).digest('hex');
}

async function main() {
  console.log('🌱 Starting database seed...');

  // Create demo user
  const demoUser = await prisma.user.upsert({
    where: { email: 'demo@autodj.io' },
    update: {},
    create: {
      email: 'demo@autodj.io',
      passwordHash: hashPassword('demo123'),
      name: 'Demo User',
      plan: Plan.PRO,
    },
  });

  console.log(`✅ Created demo user: ${demoUser.email}`);

  // Create a sample project
  const sampleProject = await prisma.project.upsert({
    where: { id: 'demo-project-1' },
    update: {},
    create: {
      id: 'demo-project-1',
      name: 'Summer House Mix',
      userId: demoUser.id,
    },
  });

  console.log(`✅ Created sample project: ${sampleProject.name}`);

  console.log('🎉 Database seed completed successfully!');
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error('❌ Seed failed:', e);
    await prisma.$disconnect();
    process.exit(1);
  });
