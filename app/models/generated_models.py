from typing import List, Optional
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer,
    PrimaryKeyConstraint, String, Text, UniqueConstraint, text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, backref
import datetime


class Base(DeclarativeBase):
    pass


class Universities(Base):
    __tablename__ = 'universities'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='universities_pkey'),
        UniqueConstraint('email_domain', name='universities_email_domain_key'),
        UniqueConstraint('name', name='universities_name_key'),
        Index('ix_universities_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email_domain: Mapped[str] = mapped_column(String)
    image_url: Mapped[Optional[str]] = mapped_column(String)

    sections: Mapped[List['Sections']] = relationship('Sections', back_populates='university')
    users: Mapped[List['Users']] = relationship('Users', back_populates='university')
    posts: Mapped[List['Posts']] = relationship('Posts', back_populates='university')


class Sections(Base):
    __tablename__ = 'sections'
    __table_args__ = (
        ForeignKeyConstraint(['university_id'], ['universities.id'], name='sections_university_id_fkey'),
        PrimaryKeyConstraint('id', name='sections_pkey'),
        Index('ix_sections_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    university_id: Mapped[int] = mapped_column(Integer)

    university: Mapped['Universities'] = relationship('Universities', back_populates='sections')
    posts: Mapped[List['Posts']] = relationship('Posts', back_populates='section')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        ForeignKeyConstraint(['university_id'], ['universities.id'], name='users_university_id_fkey'),
        PrimaryKeyConstraint('id', name='users_pkey'),
        Index('ix_users_email', 'email', unique=True),
        Index('ix_users_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    nickname: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_admin: Mapped[Optional[bool]] = mapped_column(Boolean)
    university_id: Mapped[Optional[int]] = mapped_column(Integer)
    activation_token: Mapped[Optional[str]] = mapped_column(String)
    activation_token_expiry: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    avatar_url: Mapped[Optional[str]] = mapped_column(String)
    bio: Mapped[Optional[str]] = mapped_column(String, default="")

    university: Mapped[Optional['Universities']] = relationship('Universities', back_populates='users')
    posts: Mapped[List['Posts']] = relationship('Posts', back_populates='user')
    comments: Mapped[List['Comments']] = relationship('Comments', back_populates='user')
    notifications: Mapped[List['Notifications']] = relationship('Notifications', foreign_keys='[Notifications.recipient_id]', back_populates='recipient')
    notifications_: Mapped[List['Notifications']] = relationship('Notifications', foreign_keys='[Notifications.sender_id]', back_populates='sender')
    reports: Mapped[List['Reports']] = relationship('Reports', back_populates='user')
    likes: Mapped[List['Likes']] = relationship('Likes', back_populates='user')


class Posts(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        ForeignKeyConstraint(['section_id'], ['sections.id'], name='posts_section_id_fkey'),
        ForeignKeyConstraint(['university_id'], ['universities.id'], name='posts_university_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='posts_user_id_fkey'),
        PrimaryKeyConstraint('id', name='posts_pkey'),
        Index('ix_posts_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    university_id: Mapped[int] = mapped_column(Integer)
    section_id: Mapped[int] = mapped_column(Integer)
    media_url: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    section: Mapped['Sections'] = relationship('Sections', back_populates='posts')
    university: Mapped['Universities'] = relationship('Universities', back_populates='posts')
    user: Mapped['Users'] = relationship('Users', back_populates='posts')
    comments: Mapped[List['Comments']] = relationship('Comments', back_populates='post', cascade="all, delete-orphan")
    notifications: Mapped[List['Notifications']] = relationship('Notifications', back_populates='post')
    reports: Mapped[List['Reports']] = relationship('Reports', back_populates='post')
    likes: Mapped[List['Likes']] = relationship('Likes', back_populates='post')


class Comments(Base):
    __tablename__ = 'comments'
    __table_args__ = (
        ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE', name='comments_post_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='comments_user_id_fkey'),
        # новое: self-FK для дерева
        ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='CASCADE', name='comments_parent_id_fkey'),
        PrimaryKeyConstraint('id', name='comments_pkey'),
        Index('ix_comments_id', 'id'),
        Index('ix_comments_parent_id', 'parent_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer)  # <— ДЛЯ ОТВЕТОВ
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    post: Mapped['Posts'] = relationship('Posts', back_populates='comments')
    user: Mapped['Users'] = relationship('Users', back_populates='comments')

    # self-relationship
    parent: Mapped[Optional['Comments']] = relationship(
        'Comments',
        remote_side='Comments.id',
        backref=backref('children', cascade='all, delete-orphan'),
    )

    likes: Mapped[List['Likes']] = relationship('Likes', back_populates='comment')


class Notifications(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE', name='notifications_post_id_fkey'),
        ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE', name='notifications_recipient_id_fkey'),
        ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE', name='notifications_sender_id_fkey'),
        PrimaryKeyConstraint('id', name='notifications_pkey'),
        Index('ix_notifications_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    recipient_id: Mapped[Optional[int]] = mapped_column(Integer)
    sender_id: Mapped[Optional[int]] = mapped_column(Integer)
    post_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_read: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    post: Mapped[Optional['Posts']] = relationship('Posts', back_populates='notifications')
    recipient: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[recipient_id], back_populates='notifications')
    sender: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[sender_id], back_populates='notifications_')


class Reports(Base):
    __tablename__ = 'reports'
    __table_args__ = (
        ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE', name='reports_post_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL', name='reports_user_id_fkey'),
        PrimaryKeyConstraint('id', name='reports_pkey'),
        Index('ix_reports_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))

    post: Mapped['Posts'] = relationship('Posts', back_populates='reports')
    user: Mapped[Optional['Users']] = relationship('Users', back_populates='reports')


class Likes(Base):
    __tablename__ = 'likes'
    __table_args__ = (
        ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE', name='fk_likes_comment_id'),
        ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE', name='likes_post_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='likes_user_id_fkey'),
        PrimaryKeyConstraint('id', name='likes_pkey'),
        UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_like'),
        UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
        Index('ix_likes_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    post_id: Mapped[Optional[int]] = mapped_column(Integer)
    comment_id: Mapped[Optional[int]] = mapped_column(Integer)

    comment: Mapped[Optional['Comments']] = relationship('Comments', back_populates='likes')
    post: Mapped[Optional['Posts']] = relationship('Posts', back_populates='likes')
    user: Mapped['Users'] = relationship('Users', back_populates='likes')


class Follows(Base):
    __tablename__ = 'follows'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='follows_pkey'),
        UniqueConstraint('follower_id', 'following_id', name='unique_follower_following'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    following_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
