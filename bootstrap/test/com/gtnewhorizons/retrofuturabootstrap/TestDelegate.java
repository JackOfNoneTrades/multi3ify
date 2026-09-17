package com.gtnewhorizons.retrofuturabootstrap;

public final class TestDelegate {
    public static String[] arguments;
    public static Thread thread;
    public static void main(String[] args) {
        arguments = args;
        thread = Thread.currentThread();
    }
}
